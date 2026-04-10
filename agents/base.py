# Base agent class. All agents follow the same pattern:
#   run() -> call_tools() -> build prompt -> call ollama -> parse response
#
# Subclasses only need to define: call_tools(), system_prompt, user_prompt(), output_class

from __future__ import annotations
import asyncio
import dataclasses
import json
import re
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

import requests
import config

_pool = ThreadPoolExecutor(max_workers=8)


class BaseAgent(ABC):

    name: str
    output_class: type

    def __init__(self, data: dict, tracer, phase1: dict | None = None):
        self.data   = data
        self.tracer = tracer
        self.phase1 = phase1 or {}

    async def run(self):
        sid = self.tracer.span(self.name)
        try:
            tool_out = self.call_tools()
            self.tracer.tool(self.name, tool_out)

            prompt   = self.user_prompt(tool_out)
            raw      = await self._llm(prompt)
            self.tracer.llm(self.name, raw[:100])

            result = self._parse(raw)
            self.tracer.done(sid, self.name,
                             getattr(result, "verdict", getattr(result, "decision", "?")))
            return result

        except Exception as e:
            self.tracer.error(sid, self.name, str(e))
            return self.output_class()

    @abstractmethod
    def call_tools(self) -> dict: ...

    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    @abstractmethod
    def user_prompt(self, tool_out: dict) -> str: ...

    async def _llm(self, user_msg: str) -> str:
        if config.DRY_RUN:
            await asyncio.sleep(0.05)
            return self._mock_response()

        payload = {
            "model": config.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            "stream": False,
            "options": {
                "temperature": config.TEMPERATURES.get(self.name, 0.2),
                "num_predict": 900,
            },
        }

        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                loop = asyncio.get_event_loop()
                resp = await loop.run_in_executor(
                    _pool,
                    lambda: requests.post(
                        f"{config.OLLAMA_URL}/api/chat",
                        json=payload,
                        timeout=config.OLLAMA_TIMEOUT,
                    )
                )
                resp.raise_for_status()
                return resp.json()["message"]["content"].strip()
            except Exception:
                if attempt == config.MAX_RETRIES:
                    raise
                await asyncio.sleep(2 ** attempt)

    def _mock_response(self) -> str:
        # return minimal valid JSON for this agent's schema
        fields = {f.name: f.default for f in dataclasses.fields(self.output_class)
                  if not isinstance(f.default, dataclasses._MISSING_TYPE)}
        fields["summary"] = f"[dry-run] {self.name}"
        fields["verdict"] = "PAUSE"
        return json.dumps(fields)

    def _parse(self, raw: str):
        js = self._extract_json(raw)
        if not js:
            return self.output_class()
        try:
            return self.output_class.from_dict(json.loads(js))
        except Exception:
            return self.output_class()

    @staticmethod
    def _extract_json(text: str) -> str | None:
        text = text.strip()
        if text.startswith("{"):
            return text
        m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        if m:
            return m.group(1)
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e > s:
            return text[s:e + 1]
        return None

    def _metric_table(self, metric_results: dict) -> str:
        rows = ["Metric                         | Latest   | Baseline | Change  | Status"]
        rows.append("-" * 68)
        for name, m in metric_results.items():
            if name == "__summary__" or not isinstance(m, dict):
                continue
            chg = f"{m['pct_vs_baseline']:+.0f}%"
            rows.append(
                f"{name:<31}| {str(m['latest']):<9}| {str(m['baseline']):<9}"
                f"| {chg:<8}| {m['status']} / {m['trend']}"
            )
        return "\n".join(rows)
