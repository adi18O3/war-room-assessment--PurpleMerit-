import os
from pathlib import Path

ROOT    = Path(__file__).parent
DATA    = ROOT / "data"
OUTPUTS = ROOT / "outputs"
LOGS    = ROOT / "logs"

METRICS_FILE  = DATA / "metrics.json"
FEEDBACK_FILE = DATA / "feedback.json"
NOTES_FILE    = DATA / "release_notes.md"

DECISION_FILE = OUTPUTS / "war_room_decision.json"
TRACE_FILE    = LOGS    / "trace.log"

OLLAMA_URL     = os.getenv("OLLAMA_URL",     "http://localhost:11434")
OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL",   "llama3.1:8b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
MAX_RETRIES    = int(os.getenv("MAX_RETRIES",    "3"))

# lower = more deterministic. risk agent slightly higher so it's more opinionated
TEMPERATURES = {
    "data_analyst":    float(os.getenv("TEMP_DA",   "0.1")),
    "pm_agent":        float(os.getenv("TEMP_PM",   "0.2")),
    "marketing_agent": float(os.getenv("TEMP_MKT",  "0.3")),
    "risk_agent":      float(os.getenv("TEMP_RISK", "0.25")),
}

DRY_RUN   = os.getenv("DRY_RUN",   "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def bootstrap():
    OUTPUTS.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    missing = [f for f in [METRICS_FILE, FEEDBACK_FILE, NOTES_FILE] if not f.exists()]
    if missing:
        raise FileNotFoundError(f"Missing input files: {missing}")
