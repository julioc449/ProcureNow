"""
Central configuration for ProcureNow.

API key is loaded from .env (gitignored) via python-dotenv.
Paid Gemini API — no free-tier throttling needed.
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (one level up from this file)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# ── API Key ────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")

# ── DB Layer ───────────────────────────────────────────────────────────────
DB_PATH = _env_path.parent / "data" / "procurenow.db"

# ── Model (paid tier — gemini-2.0-flash everywhere) ───────────────────────
MODEL = "gemini-3-flash-preview"
MODEL_REASONING = "gemini-3-flash-preview"

# ── Context Caching ────────────────────────────────────────────────────────
# RFP cache TTL — 1 hour is plenty for a single audit session.
CACHE_TTL = "3600s"

# ── Context Limits ─────────────────────────────────────────────────────────
MAX_CONTEXT_CHARS: int = 500_000   # Paid tier has 1M token context window

# ── Audit Batching ─────────────────────────────────────────────────────────
# Audit in batches of 10 for focused, accurate prompts.
AUDIT_BATCH_SIZE: int = 10

# ── Retry (resilience only — not rate-limit throttling) ───────────────────
MAX_RETRIES: int = 3
RETRY_BASE_DELAY_SEC: float = 5.0
RETRY_MAX_DELAY_SEC: float = 30.0
