"""
Extractor Module — Phase 2 of the compliance pipeline.

1. `get_requirements()`:          Extracts the RFP's structured requirement rubric.
2. `extract_toc_and_page_map()`:  Maps the Proposal's TOC to page ranges for routing.

Rate limiting: all Gemini calls go through rate_limiter.throttled_call().
"""
from __future__ import annotations

import json

from google import genai

from . import config
from .rate_limiter import throttled_call
from .schema import RequirementList


# ---------------------------------------------------------------------------
# Phase 2a — RFP Requirement Extraction
# ---------------------------------------------------------------------------

def get_requirements(rfp_content: str) -> RequirementList:
    """
    Extract mandatory requirements from rich Markdown RFP content (Phase 1 output).
    Uses MODEL_REASONING (gemini-2.5-flash) for accurate structured extraction.
    """
    if not config.GEMINI_API_KEY:
        print("[Extractor] No API key — using mock requirements.")
        return _get_mock_requirements()

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        truncated = rfp_content[:config.MAX_CONTEXT_CHARS]

        prompt = f"""You are an expert construction procurement officer and licensed professional engineer
specializing in public sector RFP analysis and proposal compliance.

Analyze the following RFP document and extract EVERY mandatory requirement that a responding firm must satisfy.

Pay special attention to:
- "Step 1 Deliverables" / "Proposal Documents" sections (list every required submission separately)
- Cover Letter content mandates (specific topics that must be addressed)
- Estimate format requirements — is CSI MasterFormat or Uniformat required? Note exactly which.
- General Conditions breakdown and any required allowances with dollar amounts
- Project Management Plan components
- Quality Control Plan (e.g., USACE ER 1180-1-6 compliance, designated QC Manager)
- Safety Plan and Activity Hazard Analysis (AHA) requirements
- MWDVBE / DBE / SBE participation goals — extract the exact percentage target
- Site Utilization Plan specifics
- Schedule requirements (CPM, Primavera P6, submission deadline after NTP)
- Insurance types and exact coverage amounts
- Bonding requirements and surety ratings
- Personnel qualifications (PMP, OSHA 30, PE licenses, years of experience)
- License requirements by state
- Reference project requirements (quantity, dollar value, recency window)
- Environmental compliance (SWPPP, NPDES, EPA standards)
- Debarment and legal certifications

For each requirement:
- category: pick the most specific from: Safety, Insurance, Bonding, Credentials, Environmental,
  Materials, Timeline, Staffing, Equipment, Permits, Quality Control, Financial, Legal, References,
  Technical Specifications, MWDVBE/DBE Compliance, Estimate Format, Deliverables, Site Logistics, Schedule
- requirement: EXACT text including quantities, dollar amounts, standard citations, deadlines, certifications

Be granular — one requirement per item, never bundle multiple requirements together.

RFP Document:
{truncated}"""

        response = throttled_call(
            client.models.generate_content,
            model=config.MODEL_REASONING,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": RequirementList,
            },
        )
        result = RequirementList.model_validate_json(response.text)
        print(f"[Extractor] ✅ Extracted {len(result.requirements)} requirements.")
        return result

    except Exception as e:
        print(f"[Extractor] ❌ Error: {e} — falling back to mock requirements.")
        return _get_mock_requirements()


# ---------------------------------------------------------------------------
# Phase 2b — Proposal TOC / Page-Map Extraction
# ---------------------------------------------------------------------------

def extract_toc_and_page_map(proposal_content: str) -> dict[str, tuple[int, int]]:
    """
    Build a section → (start_page, end_page) map from the Proposal's TOC.
    Sends only the first ~15k chars (where TOC always appears).
    Uses MODEL_VISION (lighter model) since this is a simple structured task.
    """
    if not config.GEMINI_API_KEY:
        return {}

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        toc_section = proposal_content[:15_000]

        prompt = f"""Extract the Table of Contents from this construction proposal document.

Return a JSON object mapping each section name to [start_page, end_page].
Example: {{"Cover Letter": [1, 2], "CSI Estimate": [3, 45], "Safety Plan": [46, 60]}}

Rules:
- Use exact section names as they appear in the TOC
- Estimate end pages from next section's start
- If no TOC visible, return {{}}

Document:
{toc_section}"""

        response = throttled_call(
            client.models.generate_content,
            model=config.MODEL_VISION,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )

        raw = json.loads(response.text)
        page_map: dict[str, tuple[int, int]] = {}
        for section, pages in raw.items():
            if isinstance(pages, list) and len(pages) == 2:
                page_map[section] = (int(pages[0]), int(pages[1]))
        print(f"[Extractor] ✅ TOC: mapped {len(page_map)} sections.")
        return page_map

    except Exception as e:
        print(f"[Extractor] TOC extraction failed: {e} — auditor will use full document.")
        return {}


# ---------------------------------------------------------------------------
# Mock data for demo / no-key fallback
# ---------------------------------------------------------------------------

def _get_mock_requirements() -> RequirementList:
    """Comprehensive mock requirements for testing without an API key."""
    mock_data = {
        "requirements": [
            {"category": "Safety", "requirement": "Must provide a comprehensive site safety plan conforming to OSHA 29 CFR 1926 standards, including fall protection, excavation safety, and hazardous materials handling procedures."},
            {"category": "Safety", "requirement": "Contractor shall designate a full-time on-site safety officer with OSHA 30-Hour certification."},
            {"category": "Insurance", "requirement": "General liability insurance of at least $2,000,000 per occurrence and $5,000,000 aggregate."},
            {"category": "Insurance", "requirement": "Workers' compensation insurance as required by state law, with a minimum Experience Modification Rate (EMR) of 1.0 or below."},
            {"category": "Bonding", "requirement": "Performance bond equal to 100% of the contract value from a surety rated A-VII or better by AM Best."},
            {"category": "Bonding", "requirement": "Payment bond equal to 100% of the contract value per the Miller Act requirements."},
            {"category": "Credentials", "requirement": "Contractor must hold a valid General Contractor license in the state where work is performed."},
            {"category": "Credentials", "requirement": "Firm must demonstrate a minimum of 10 years of experience in commercial construction projects exceeding $5M."},
            {"category": "Credentials", "requirement": "Project Manager must hold PMP certification and have managed at least 3 projects of similar scope."},
            {"category": "Environmental", "requirement": "Submit a Stormwater Pollution Prevention Plan (SWPPP) compliant with NPDES permit requirements."},
            {"category": "Environmental", "requirement": "All hazardous waste disposal must comply with EPA 40 CFR Part 261 regulations."},
            {"category": "Materials", "requirement": "All concrete must meet ASTM C94/C94M specifications with minimum 4,000 PSI compressive strength at 28 days."},
            {"category": "Materials", "requirement": "Structural steel shall conform to ASTM A992/A992M and be domestically sourced per Buy America provisions."},
            {"category": "Timeline", "requirement": "Project must be substantially complete within 18 months of Notice to Proceed."},
            {"category": "Timeline", "requirement": "Contractor shall submit a CPM schedule within 30 days of NTP showing all major milestones."},
            {"category": "Staffing", "requirement": "Provide resumes for all key personnel including Project Manager, Superintendent, and Quality Control Manager."},
            {"category": "Financial", "requirement": "Submit audited financial statements for the last 3 fiscal years demonstrating financial capacity."},
            {"category": "References", "requirement": "Provide at least 5 references from completed projects of similar scope within the last 7 years."},
            {"category": "Quality Control", "requirement": "Implement a Quality Control Plan per USACE ER 1180-1-6 with designated QC Manager."},
            {"category": "Legal", "requirement": "Certify that the firm has not been debarred or suspended from federal contracting."},
        ]
    }
    return RequirementList.model_validate(mock_data)
