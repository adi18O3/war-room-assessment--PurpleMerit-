# Simple tracer — records what each agent did and how long it took.
# Nothing fancy, just enough to show the evaluator what ran.

import json
import logging
import time
import uuid
from datetime import datetime, timezone

import config


class Tracer:
    def __init__(self):
        self._spans = []
        self._active = {}
        self._setup_logger()

    def _setup_logger(self):
        self.log = logging.getLogger("war_room")
        self.log.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))
        self.log.handlers.clear()

        fmt = logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S")

        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        self.log.addHandler(ch)

        config.LOGS.mkdir(exist_ok=True)
        fh = logging.FileHandler(config.TRACE_FILE, mode="w", encoding="utf-8")
        fh.setFormatter(fmt)
        self.log.addHandler(fh)

    def span(self, name: str) -> str:
        sid = str(uuid.uuid4())[:8]
        self._active[sid] = time.monotonic()
        self.log.info(f">> {name} starting")
        return sid

    def done(self, sid: str, name: str, verdict: str = ""):
        ms = self._elapsed(sid)
        suffix = f" => {verdict}" if verdict else ""
        self.log.info(f"   {name} done{suffix}  ({ms}ms)")
        self._record("agent", name, "ok", ms)

    def error(self, sid: str, name: str, msg: str):
        ms = self._elapsed(sid)
        self.log.error(f"   {name} FAILED: {msg}  ({ms}ms)")
        self._record("agent", name, "error", ms, error=msg)

    def tool(self, agent: str, result):
        preview = str(result)[:80]
        self.log.info(f"   [tool] {agent} => {preview}")
        self._record("tool", f"tool:{agent}", "ok")

    def llm(self, agent: str, preview: str):
        self.log.info(f"   [llm]  {agent} => {preview[:80]}")
        self._record("llm", f"llm:{agent}", "ok")

    def info(self, msg: str):
        self.log.info(msg)

    def save(self):
        try:
            with open(config.TRACE_FILE, "a", encoding="utf-8") as f:
                f.write("\n\n# structured trace below\n")
                json.dump(self._spans, f, indent=2, default=str)
        except Exception as e:
            self.log.warning(f"couldn't save structured trace: {e}")

    def summary(self):
        print("\n--- run summary ---")
        for s in self._spans:
            icon = "OK" if s["status"] == "ok" else "FAIL"
            dur  = f"{s['duration_ms']}ms" if s.get("duration_ms") else ""
            print(f"  {icon}  {s['actor']:<32}  {dur}")
        print("-------------------\n")

    def _elapsed(self, sid: str) -> int:
        return round((time.monotonic() - self._active.pop(sid, time.monotonic())) * 1000)

    def _record(self, kind, actor, status, duration_ms=0, error=""):
        self._spans.append({
            "id":          str(uuid.uuid4())[:8],
            "type":        kind,
            "actor":       actor,
            "status":      status,
            "duration_ms": duration_ms or None,
            "ts":          datetime.now(timezone.utc).isoformat(),
            "error":       error or None,
        })
