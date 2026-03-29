"""
Auditor Module — Phase 3 of the compliance pipeline.

Evaluates each RFP requirement against the proposal using 3 criteria:
  1. Presence  — Is the item included at all?
  2. Accuracy  — Does it match the required format/standard/amount?
  3. Context   — Does it address specific RFP constraints (MWDVBE %, etc.)?

Batching: requirements are evaluated in groups of AUDIT_BATCH_SIZE (default 8).
  - Keeps each prompt focused and within safe token limits.
  - throttled_call() adds INTER_CALL_DELAY_SEC between batches (12s default).
  - This means 20 requirements → 3 batches → safe even on free-tier AI Studio.

Rate limiting: all Gemini calls go through rate_limiter.throttled_call().
"""
from __future__ import annotations

import json
import re

from google import genai

from . import config
from .rate_limiter import throttled_call
from .schema import ComplianceObject, RequirementList, AuditReport


# ---------------------------------------------------------------------------
# Proposal section routing
# ---------------------------------------------------------------------------

def chunk_proposal_by_section(
    proposal_content: str,
    page_map: dict[str, tuple[int, int]],
) -> dict[str, str]:
    """Split proposal into named sections using the TOC page map."""
    if not page_map:
        return {"_full": proposal_content}

    page_positions: dict[int, int] = {}
    for m in re.finditer(r"--- PAGE (\d+) ---", proposal_content):
        page_positions[int(m.group(1))] = m.start()

    if not page_positions:
        return {"_full": proposal_content}

    max_page = max(page_positions.keys())

    def get_slice(start: int, end: int) -> str:
        s_off = next((page_positions[p] for p in sorted(page_positions) if p >= start), None)
        if s_off is None:
            return ""
        e_page = min(end + 1, max_page + 1)
        e_off = next((page_positions[p] for p in sorted(page_positions) if p >= e_page), None)
        return proposal_content[s_off:e_off] if e_off else proposal_content[s_off:]

    return {section: get_slice(s, e) for section, (s, e) in page_map.items()}


# ---------------------------------------------------------------------------
# Single-batch audit call
# ---------------------------------------------------------------------------

def _audit_batch(
    client,
    batch_requirements: list,
    proposal_excerpt: str,
    proposal_id: str,
    batch_num: int,
    total_batches: int,
) -> list[ComplianceObject]:
    """
    Audit a single batch of requirements against the given proposal excerpt.
    Returns a list of ComplianceObject results (one per requirement in batch).
    """
    req_json = json.dumps([
        {"category": r.category, "requirement": r.requirement}
        for r in batch_requirements
    ], indent=2)

    # Truncate excerpt to safe size for reasonining model
    excerpt = proposal_excerpt[:config.MAX_CONTEXT_CHARS]

    prompt = f"""You are a licensed professional engineer performing a construction proposal compliance audit.

Batch {batch_num} of {total_batches} — evaluate the following {len(batch_requirements)} requirements.

THREE-CRITERIA EVALUATION per requirement:
1. PRESENCE    — Is the document/section included at all?
2. ACCURACY    — Does it match the exact format/standard/amount required?
   (e.g., CSI MasterFormat vs Uniformat, specific $ amounts, OSHA codes, certification numbers)
3. CONTEXT     — Does it address specific RFP constraints?
   (MWDVBE %, Activity Hazard Analysis specifics, high-risk scope narratives)

For each requirement return:
- status: "Complete" (all 3 pass) / "Partial" (1-2 pass) / "Incomplete" (none pass)
- confidence_score: 0.0-1.0
- proposal_evidence: direct quote or summary; null if nothing found
- missing_elements: list of specific gaps; empty if Complete
- page_reference: page number from --- PAGE N --- markers; null if not found
- evidence_page: same as page_reference
- format_match: true/false if a format requirement exists; null otherwise
- percentage_filled: 0-100

⚠️ Flag as Partial rather than Complete for ANY ambiguity.
⚠️ Priority checks: estimate format (CSI vs Uniformat), MWDVBE % goal, bonding surety ratings,
   OSHA/EPA standard citations, personnel certification numbers.

Return a JSON array of {len(batch_requirements)} objects in the SAME ORDER as the requirements list.

Requirements:
{req_json}

Proposal content:
{excerpt}"""

    response = throttled_call(
        client.models.generate_content,
        model=config.MODEL_REASONING,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    raw = json.loads(response.text)
    results = []
    for i, r in enumerate(batch_requirements):
        d = raw[i] if i < len(raw) else {}
        results.append(ComplianceObject(
            category=r.category,
            requirement=r.requirement,
            status=d.get("status", "Incomplete"),
            confidence_score=float(d.get("confidence_score", 0.5)),
            proposal_evidence=d.get("proposal_evidence"),
            missing_elements=d.get("missing_elements", []),
            page_reference=d.get("page_reference"),
            evidence_page=d.get("evidence_page"),
            format_match=d.get("format_match"),
            percentage_filled=float(d.get("percentage_filled", 0.0)),
        ))
    return results


# ---------------------------------------------------------------------------
# Main audit orchestrator
# ---------------------------------------------------------------------------

def audit_proposal(
    proposal_text: str,
    requirements: RequirementList,
    proposal_id: str = "proposal_001",
    rfp_name: str = "",
    page_map: dict | None = None,
) -> AuditReport:
    """
    Phase 3: Cross-verify all RFP requirements against the proposal.

    Requirements are processed in batches of AUDIT_BATCH_SIZE (default 8) to:
    - Keep each prompt focused and within safe token limits.
    - Naturally pace calls via throttled_call() to avoid 429 rate limits.
    - Maintain full analysis quality without truncating requirements.
    """
    if not config.GEMINI_API_KEY:
        print("[Auditor] No API key — using mock audit.")
        return _get_mock_audit(requirements, proposal_id, rfp_name)

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)

        # Route proposal into sections if we have a page map
        sections = chunk_proposal_by_section(proposal_text, page_map or {})
        # For most requirements, use the full (truncated) proposal unless we have specific routing
        full_excerpt = proposal_text[:config.MAX_CONTEXT_CHARS]

        reqs = requirements.requirements
        batch_size = config.AUDIT_BATCH_SIZE
        batches = [reqs[i:i + batch_size] for i in range(0, len(reqs), batch_size)]
        total_batches = len(batches)
        print(f"[Auditor] {len(reqs)} requirements → {total_batches} batch(es) of ≤{batch_size}.")

        all_results: list[ComplianceObject] = []
        for idx, batch in enumerate(batches, 1):
            print(f"[Auditor] Processing batch {idx}/{total_batches} "
                  f"({len(batch)} requirements)...")
            try:
                batch_results = _audit_batch(
                    client=client,
                    batch_requirements=batch,
                    proposal_excerpt=full_excerpt,
                    proposal_id=proposal_id,
                    batch_num=idx,
                    total_batches=total_batches,
                )
                all_results.extend(batch_results)
            except Exception as e:
                print(f"[Auditor] Batch {idx} failed: {e} — marking as Incomplete.")
                for r in batch:
                    all_results.append(ComplianceObject(
                        category=r.category,
                        requirement=r.requirement,
                        status="Incomplete",
                        confidence_score=0.0,
                        missing_elements=[f"Audit error: {str(e)[:80]}"],
                        percentage_filled=0.0,
                    ))

        # Generate critical omissions summary
        critical_reqs = [
            r for r in all_results
            if r.status == "Incomplete" and r.category in (
                "Financial", "Environmental", "Bonding", "Deliverables",
                "Estimate Format", "MWDVBE/DBE Compliance", "Safety"
            )
        ]
        critical_omissions = [
            f"{r.category}: {r.requirement[:90]}…" if len(r.requirement) > 90 else f"{r.category}: {r.requirement}"
            for r in critical_reqs[:5]
        ]

        report = AuditReport(
            proposal_id=proposal_id,
            rfp_name=rfp_name,
            audit_results=all_results,
            critical_omissions=critical_omissions,
        )
        print(f"[Auditor] ✅ Complete: {report.complete_count}✓ "
              f"{report.partial_count}~ {report.incomplete_count}✗ "
              f"— {report.overall_percentage}% overall.")
        if critical_omissions:
            print(f"[Auditor] ⚠️  Critical: {critical_omissions}")
        return report

    except Exception as e:
        print(f"[Auditor] ❌ Pipeline error: {e} — falling back to mock audit.")
        return _get_mock_audit(requirements, proposal_id, rfp_name)


# ---------------------------------------------------------------------------
# Mock audit (demo / no-key fallback)
# ---------------------------------------------------------------------------

def _get_mock_audit(requirements: RequirementList, proposal_id: str, rfp_name: str) -> AuditReport:
    """Realistic mock audit for demo without an API key."""
    results = []
    mock_statuses = {
        "Safety": [
            {"status": "Complete", "confidence_score": 0.95, "percentage_filled": 100.0,
             "proposal_evidence": "Section 4.1 — comprehensive site safety plan per OSHA 29 CFR 1926 including fall protection, excavation safety, and hazardous materials handling.",
             "missing_elements": [], "page_reference": 4, "evidence_page": 4, "format_match": True},
            {"status": "Partial", "confidence_score": 0.75, "percentage_filled": 60.0,
             "proposal_evidence": "Safety officer will be assigned; full-time on-site presence not confirmed.",
             "missing_elements": ["Full-time on-site designation not confirmed", "OSHA 30-Hour cert not provided"],
             "page_reference": 5, "evidence_page": 5, "format_match": None},
        ],
        "Insurance": [
            {"status": "Partial", "confidence_score": 0.80, "percentage_filled": 50.0,
             "proposal_evidence": "We maintain comprehensive general liability insurance for all construction projects.",
             "missing_elements": ["$2M per-occurrence not stated", "$5M aggregate not confirmed"],
             "page_reference": 12, "evidence_page": 12, "format_match": False},
            {"status": "Incomplete", "confidence_score": 0.90, "percentage_filled": 0.0,
             "proposal_evidence": None,
             "missing_elements": ["Workers' comp not provided", "EMR not disclosed"],
             "page_reference": None, "evidence_page": None, "format_match": None},
        ],
        "Bonding": [
            {"status": "Complete", "confidence_score": 0.92, "percentage_filled": 100.0,
             "proposal_evidence": "Performance bond 100% contract value — Zurich Insurance, A+ XV by AM Best.",
             "missing_elements": [], "page_reference": 14, "evidence_page": 14, "format_match": True},
            {"status": "Complete", "confidence_score": 0.90, "percentage_filled": 100.0,
             "proposal_evidence": "Payment bond 100% contract value per Miller Act.",
             "missing_elements": [], "page_reference": 14, "evidence_page": 14, "format_match": True},
        ],
        "Credentials": [
            {"status": "Complete", "confidence_score": 0.98, "percentage_filled": 100.0,
             "proposal_evidence": "License No. CGC-12345 valid 12/2027 — copy in Appendix B.",
             "missing_elements": [], "page_reference": 2, "evidence_page": 2, "format_match": True},
            {"status": "Complete", "confidence_score": 0.93, "percentage_filled": 100.0,
             "proposal_evidence": "Founded 2008 — 22 commercial projects >$5M in 17 years.",
             "missing_elements": [], "page_reference": 3, "evidence_page": 3, "format_match": True},
            {"status": "Partial", "confidence_score": 0.65, "percentage_filled": 40.0,
             "proposal_evidence": "John Smith, PM — 12 years experience on large commercial projects.",
             "missing_elements": ["PMP certification not mentioned", "Only 2 similar-scope projects (3 required)"],
             "page_reference": 8, "evidence_page": 8, "format_match": None},
        ],
        "Environmental": [
            {"status": "Incomplete", "confidence_score": 0.88, "percentage_filled": 0.0,
             "proposal_evidence": None,
             "missing_elements": ["SWPPP not included", "NPDES compliance not addressed"],
             "page_reference": None, "evidence_page": None, "format_match": None},
            {"status": "Partial", "confidence_score": 0.70, "percentage_filled": 30.0,
             "proposal_evidence": "All waste disposed per applicable regulations.",
             "missing_elements": ["EPA 40 CFR Part 261 not cited", "Hazardous waste procedures not detailed"],
             "page_reference": 22, "evidence_page": 22, "format_match": None},
        ],
        "Materials": [
            {"status": "Complete", "confidence_score": 0.96, "percentage_filled": 100.0,
             "proposal_evidence": "Concrete — ASTM C94/C94M, min 4,000 PSI at 28 days per Sec. 03300.",
             "missing_elements": [], "page_reference": 18, "evidence_page": 18, "format_match": True},
            {"status": "Partial", "confidence_score": 0.72, "percentage_filled": 55.0,
             "proposal_evidence": "Steel per ASTM A992.",
             "missing_elements": ["Buy America cert not provided", "ASTM A992M not referenced"],
             "page_reference": 19, "evidence_page": 19, "format_match": None},
        ],
        "Timeline": [
            {"status": "Complete", "confidence_score": 0.94, "percentage_filled": 100.0,
             "proposal_evidence": "Substantial completion within 16 months of NTP — 2 months ahead of requirement.",
             "missing_elements": [], "page_reference": 6, "evidence_page": 6, "format_match": True},
            {"status": "Incomplete", "confidence_score": 0.85, "percentage_filled": 0.0,
             "proposal_evidence": None,
             "missing_elements": ["CPM schedule not included", "30-day submittal not addressed"],
             "page_reference": None, "evidence_page": None, "format_match": None},
        ],
        "Staffing": [
            {"status": "Partial", "confidence_score": 0.78, "percentage_filled": 65.0,
             "proposal_evidence": "Resumes — John Smith (PM), Mike Johnson (Super) in Appendix C.",
             "missing_elements": ["QC Manager resume not provided"],
             "page_reference": 30, "evidence_page": 30, "format_match": None},
        ],
        "Financial": [
            {"status": "Incomplete", "confidence_score": 0.92, "percentage_filled": 0.0,
             "proposal_evidence": None,
             "missing_elements": ["Audited financial statements not included", "3 years of records required"],
             "page_reference": None, "evidence_page": None, "format_match": None},
        ],
        "References": [
            {"status": "Partial", "confidence_score": 0.82, "percentage_filled": 60.0,
             "proposal_evidence": "3 references: City Hall (2022), Harbor Bridge (2023), Water Plant (2021).",
             "missing_elements": ["Only 3 references (5 required)", "Contact info incomplete for 1"],
             "page_reference": 35, "evidence_page": 35, "format_match": None},
        ],
        "Quality Control": [
            {"status": "Partial", "confidence_score": 0.68, "percentage_filled": 45.0,
             "proposal_evidence": "QC program includes inspections and material testing.",
             "missing_elements": ["USACE ER 1180-1-6 not referenced", "QC Manager not named"],
             "page_reference": 24, "evidence_page": 24, "format_match": None},
        ],
        "Legal": [
            {"status": "Complete", "confidence_score": 0.97, "percentage_filled": 100.0,
             "proposal_evidence": "Certified not debarred — SAM.gov #ABCD1234.",
             "missing_elements": [], "page_reference": 40, "evidence_page": 40, "format_match": True},
        ],
    }

    for req in requirements.requirements:
        cat = req.category
        if cat in mock_statuses and mock_statuses[cat]:
            m = mock_statuses[cat].pop(0)
        else:
            m = {"status": "Incomplete", "confidence_score": 0.85, "percentage_filled": 0.0,
                 "proposal_evidence": None,
                 "missing_elements": [f"No information found: {req.requirement}"],
                 "page_reference": None, "evidence_page": None, "format_match": None}
        results.append(ComplianceObject(category=req.category, requirement=req.requirement, **m))

    critical = [
        f"{r.category}: {r.requirement[:80]}…" for r in results
        if r.status == "Incomplete" and r.category in ("Financial", "Environmental", "Bonding")
    ][:5]

    return AuditReport(
        proposal_id=proposal_id,
        rfp_name=rfp_name,
        audit_results=results,
        critical_omissions=critical,
    )
