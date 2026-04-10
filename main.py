"""
War Room — multi-agent launch decision system.

Usage:
    python main.py               # full run (needs ollama running)
    python main.py --dry-run     # no LLM calls, useful for testing
    python main.py --model mistral:7b
"""
import argparse
import asyncio
import json
import os
import sys


def get_args():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run",   action="store_true")
    p.add_argument("--model",     type=str, default=None)
    p.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING"], default=None)
    return p.parse_args()


# set env before importing config so values are picked up correctly
args = get_args()
if args.dry_run:   os.environ["DRY_RUN"]     = "true"
if args.model:     os.environ["OLLAMA_MODEL"] = args.model
if args.log_level: os.environ["LOG_LEVEL"]   = args.log_level

try:
    from dotenv import load_dotenv
    load_dotenv()
    # re-apply cli args in case .env overwrote them
    if args.dry_run:   os.environ["DRY_RUN"]     = "true"
    if args.model:     os.environ["OLLAMA_MODEL"] = args.model
except ImportError:
    pass

import config
from tracer import Tracer


def load_inputs() -> dict:
    with open(config.METRICS_FILE,  encoding="utf-8") as f:
        metrics = json.load(f)
    with open(config.FEEDBACK_FILE, encoding="utf-8") as f:
        feedback = json.load(f)
    with open(config.NOTES_FILE,    encoding="utf-8") as f:
        notes = f.read()
    return {"metrics": metrics, "feedback": feedback, "notes": notes}


async def check_ollama(tracer) -> bool:
    if config.DRY_RUN:
        tracer.info("ollama check    skipped (dry-run)")
        return True
    import requests
    try:
        resp   = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        ok     = any(config.OLLAMA_MODEL in m or m in config.OLLAMA_MODEL for m in models)
        if ok:
            tracer.info(f"ollama check    ok — {config.OLLAMA_MODEL} ready")
            return True
        tracer.log.error(
            f"model '{config.OLLAMA_MODEL}' not found. available: {models}\n"
            f"run: ollama pull {config.OLLAMA_MODEL}"
        )
        return False
    except Exception as e:
        tracer.log.error(f"can't reach ollama at {config.OLLAMA_URL}: {e}\ntry: ollama serve")
        return False


async def main():
    config.bootstrap()

    print(f"\nmodel:   {config.OLLAMA_MODEL}")
    print(f"dry-run: {config.DRY_RUN}\n")

    tracer = Tracer()

    if not await check_ollama(tracer):
        sys.exit(1)

    data = load_inputs()
    tracer.info(
        f"loaded  {len(data['metrics']['metrics'])} metrics  |  "
        f"{data['feedback']['total']} feedback entries"
    )

    from orchestrator import WarRoomOrchestrator
    result = await WarRoomOrchestrator(data, tracer).run()

    with open(config.DECISION_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    tracer.save()
    tracer.summary()

    print(f"\n{'='*48}")
    print(f"  decision    : {result['decision']}")
    print(f"  confidence  : {result['confidence_score']:.0%}")
    print(f"  votes       : {result['agent_votes']}")
    print(f"  output      : {config.DECISION_FILE}")
    print(f"  trace       : {config.TRACE_FILE}")
    print(f"{'='*48}\n")


if __name__ == "__main__":
    asyncio.run(main())
