"""
PDF Ingestion Module — Phase 1 of the compliance pipeline.

Functions:
  - `ingest_and_cache_rfp()`:   Uploads RFP PDF, extracts content, and creates a
                                 Gemini context cache so downstream calls (requirements
                                 extraction, audit cross-reference) reuse the same
                                 cached tokens instead of re-sending the full document.
  - `ingest_pdf_multimodal()`:  Standard ingestion for non-RFP docs (Proposal).
  - `extract_text_from_bytes()`: Fast PyMuPDF text-only fallback.
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

import fitz  # PyMuPDF

from . import config
from .rate_limiter import throttled_call


# ---------------------------------------------------------------------------
# Text-only fallback (no API)
# ---------------------------------------------------------------------------

def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts = []
    for i in range(len(doc)):
        text = doc[i].get_text("text")
        if text.strip():
            parts.append(f"--- PAGE {i + 1} ---\n{text}")
    doc.close()
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Shared upload helper
# ---------------------------------------------------------------------------

def _upload_and_wait(client, pdf_bytes: bytes, label: str):
    """Upload PDF bytes to Gemini File API and wait until ACTIVE."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        print(f"[PDF] Uploading {label} ({len(pdf_bytes):,} bytes)...")
        pdf_file = client.files.upload(
            file=tmp_path,
            config={"mime_type": "application/pdf"},
        )
        waited = 0
        while pdf_file.state.name == "PROCESSING" and waited < 120:
            time.sleep(2)
            waited += 2
            pdf_file = client.files.get(name=pdf_file.name)
        if pdf_file.state.name != "ACTIVE":
            raise RuntimeError(f"File stuck in state: {pdf_file.state.name}")
        print(f"[PDF] {label} file active.")
        return pdf_file
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _page_count(pdf_bytes: bytes) -> int:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n = len(doc)
    doc.close()
    return n


# ---------------------------------------------------------------------------
# RFP ingestion WITH context caching (the key new feature)
# ---------------------------------------------------------------------------

def ingest_and_cache_rfp(pdf_bytes: bytes) -> tuple[str, str | None]:
    """
    Upload the RFP PDF, extract its full Markdown content, and create a
    Gemini context cache for the document.

    Context caching means the RFP is tokenized ONCE and stored server-side.
    Subsequent calls that reference `cache_name` skip re-sending the full
    document — reducing latency and cost on paid tier.

    Args:
        pdf_bytes: Raw RFP PDF bytes.

    Returns:
        (content_str, cache_name)
        content_str: Full Markdown extraction of the RFP.
        cache_name:  Gemini cache resource name (e.g. "cachedContents/abc123"),
                     or None if caching failed (pipeline continues without it).
    """
    if not config.GEMINI_API_KEY:
        print("[PDF] No API key — text-only fallback.")
        return extract_text_from_bytes(pdf_bytes), None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=config.GEMINI_API_KEY)
        num_pages = _page_count(pdf_bytes)
        pdf_file = _upload_and_wait(client, pdf_bytes, "RFP")

        # ── Create context cache ─────────────────────────────────────────
        cache_name: str | None = None
        try:
            print("[PDF] Creating context cache for RFP...")
            cache = client.caches.create(
                model=config.MODEL,
                config=types.CreateCachedContentConfig(
                    display_name="ProcureNow RFP Cache",
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_uri(
                                file_uri=pdf_file.uri,
                                mime_type="application/pdf",
                            )],
                        )
                    ],
                    ttl=config.CACHE_TTL,
                ),
            )
            cache_name = cache.name
            print(f"[PDF] ✅ Context cache created: {cache_name}")
        except Exception as ce:
            # Cache creation fails for docs below the minimum token threshold
            print(f"[PDF] Cache creation failed (doc may be below min tokens): {ce}")
            print("[PDF] Continuing without cache — full content will be sent per call.")

        # ── Extract full Markdown content from the uploaded file ─────────
        extraction_prompt = f"""Convert this RFP PDF ({num_pages} pages) to structured Markdown.

Rules:
1. Start each page: `--- PAGE N ---`
2. Preserve ALL section headings using ## / ###
3. Tables → Markdown |col|col| format, ALL rows and columns
4. Financial data (CSI, Uniformat, estimates) → preserve every line-item, code, dollar amount
5. Charts/Gantt/org-charts → bullet-point description with dates, milestones, roles
6. Images → [IMAGE: brief description]
7. Preserve ALL numbers, certification numbers, dollar figures, dates, OSHA/EPA codes exactly"""

        if cache_name:
            # Use the cache for extraction
            response = throttled_call(
                client.models.generate_content,
                model=config.MODEL,
                contents=[extraction_prompt],
                config=types.GenerateContentConfig(cached_content=cache_name),
            )
        else:
            response = throttled_call(
                client.models.generate_content,
                model=config.MODEL,
                contents=[pdf_file, extraction_prompt],
            )

        content = response.text
        print(f"[PDF] ✅ RFP extracted — {len(content):,} chars / {num_pages} pages.")

        # Clean up the uploaded file (cache references it internally)
        try:
            client.files.delete(name=pdf_file.name)
        except Exception:
            pass

        return content, cache_name

    except Exception as e:
        print(f"[PDF] ❌ RFP multimodal failed: {e} — text-only fallback.")
        return extract_text_from_bytes(pdf_bytes), None


# ---------------------------------------------------------------------------
# Proposal ingestion — standard multimodal (no cache needed)
# ---------------------------------------------------------------------------

def ingest_pdf_multimodal(pdf_bytes: bytes, label: str = "Proposal") -> str:
    """
    Upload and extract a PDF (typically the Proposal) without caching.
    Returns full Markdown content string.
    """
    if not config.GEMINI_API_KEY:
        print(f"[PDF] No API key — text-only fallback for {label}.")
        return extract_text_from_bytes(pdf_bytes)

    try:
        from google import genai

        client = genai.Client(api_key=config.GEMINI_API_KEY)
        num_pages = _page_count(pdf_bytes)
        pdf_file = _upload_and_wait(client, pdf_bytes, label)

        prompt = f"""Convert this {label} PDF ({num_pages} pages) to structured Markdown.

Rules:
1. Start each page: `--- PAGE N ---`
2. Preserve ALL section headings using ## / ###
3. Tables → Markdown |col|col| format, ALL rows and columns
4. Financial data (CSI, Uniformat, estimates) → preserve every line-item, code, dollar amount
5. Charts/Gantt/org-charts → bullet-point description with dates, milestones, roles
6. Images → [IMAGE: brief description]
7. Preserve ALL numbers, certification numbers, dollar figures, dates, OSHA/EPA codes exactly"""

        response = throttled_call(
            client.models.generate_content,
            model=config.MODEL,
            contents=[pdf_file, prompt],
        )

        try:
            client.files.delete(name=pdf_file.name)
        except Exception:
            pass

        content = response.text
        print(f"[PDF] ✅ {label} extracted — {len(content):,} chars / {num_pages} pages.")
        return content

    except Exception as e:
        print(f"[PDF] ❌ {label} multimodal failed: {e} — text-only fallback.")
        return extract_text_from_bytes(pdf_bytes)
