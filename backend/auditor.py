"""
Auditor Module — Semantic gap analysis of proposal vs. RFP requirements.

Hackathon: Single Gemini call with structured JSON output.
Future: Multi-step agentic workflow (LangGraph) with self-reflection.
"""
import os
from google import genai
from .schema import ComplianceObject, RequirementList, AuditReport


MAX_CONTEXT_CHARS = 120_000


def audit_proposal(
    proposal_text: str,
    requirements: RequirementList,
    proposal_id: str = "proposal_001",
    rfp_name: str = "",
) -> AuditReport:
    """
    Compares proposal text against extracted RFP requirements.

    Args:
        proposal_text: Full text extracted from the proposal/submittal PDF.
        requirements: Structured requirements extracted from the RFP.
        proposal_id: Unique identifier for this audit run.
        rfp_name: Name of the RFP document.

    Returns:
        AuditReport with per-requirement compliance results.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[Auditor] GEMINI_API_KEY not found — using mock audit.")
        return _get_mock_audit(requirements, proposal_id, rfp_name)

    try:
        client = genai.Client(api_key=api_key)

        req_json = requirements.model_dump_json()
        truncated_proposal = proposal_text[:MAX_CONTEXT_CHARS]

        prompt = f"""You are an expert civil engineering compliance auditor reviewing a construction proposal against mandatory RFP requirements.

For EACH requirement in the list below, carefully analyze the submitted proposal and determine:

1. **status**: "Complete" if fully addressed, "Partial" if some elements present but not all, "Incomplete" if not addressed at all.
2. **confidence_score**: Your confidence in the assessment (0.0-1.0).
3. **proposal_evidence**: Direct quote or summary from the proposal that supports your determination. Use "N/A" if nothing found.
4. **missing_elements**: List specific items that are missing or insufficient. Empty list if Complete.
5. **page_reference**: The page number where you found the evidence (from the "--- PAGE X ---" markers). null if not found.
6. **percentage_filled**: How much of this requirement has been addressed (0-100). Complete=100, Incomplete=0, Partial=estimated %.

Be thorough and precise. Err on the side of marking something as Partial rather than Complete if there is any ambiguity.

Focus especially on:
- Safety compliance (OSHA, site safety plans)
- Insurance coverage amounts and types
- Company credentials, licenses, certifications
- Risk identification and mitigation
- Environmental compliance
- Financial qualifications

Proposal ID: {proposal_id}

RFP Requirements List:
{req_json}

Submitted Proposal Content:
{truncated_proposal}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": AuditReport,
            },
        )
        result = AuditReport.model_validate_json(response.text)
        print(f"[Auditor] Audit complete: {result.complete_count}/{result.total_requirements} requirements met.")
        return result

    except Exception as e:
        print(f"[Auditor] LLM error: {e} — falling back to mock audit.")
        return _get_mock_audit(requirements, proposal_id, rfp_name)


def _get_mock_audit(requirements: RequirementList, proposal_id: str, rfp_name: str) -> AuditReport:
    """Realistic mock audit for testing without an API key."""
    results = []

    # Assign realistic statuses based on category for demo purposes
    mock_statuses = {
        "Safety": [
            {"status": "Complete", "confidence_score": 0.95, "percentage_filled": 100.0,
             "proposal_evidence": "Section 4.1 contains a comprehensive site safety plan that addresses OSHA 29 CFR 1926 standards including fall protection protocols, excavation safety measures, and hazardous materials handling procedures.",
             "missing_elements": [], "page_reference": 4},
            {"status": "Partial", "confidence_score": 0.75, "percentage_filled": 60.0,
             "proposal_evidence": "The proposal mentions a safety officer will be assigned but does not specify full-time on-site presence.",
             "missing_elements": ["Full-time on-site designation not confirmed", "OSHA 30-Hour certification documentation not provided"], "page_reference": 5},
        ],
        "Insurance": [
            {"status": "Partial", "confidence_score": 0.80, "percentage_filled": 50.0,
             "proposal_evidence": "We maintain comprehensive general liability insurance coverage for all construction projects.",
             "missing_elements": ["Specific per-occurrence amount of $2,000,000 not stated", "Aggregate limit of $5,000,000 not confirmed"], "page_reference": 12},
            {"status": "Incomplete", "confidence_score": 0.90, "percentage_filled": 0.0,
             "proposal_evidence": None,
             "missing_elements": ["Workers' compensation insurance details not provided", "Experience Modification Rate (EMR) not disclosed"], "page_reference": None},
        ],
        "Bonding": [
            {"status": "Complete", "confidence_score": 0.92, "percentage_filled": 100.0,
             "proposal_evidence": "Performance bond at 100% contract value will be provided by Zurich Insurance, rated A+ XV by AM Best.",
             "missing_elements": [], "page_reference": 14},
            {"status": "Complete", "confidence_score": 0.90, "percentage_filled": 100.0,
             "proposal_evidence": "Payment bond at 100% contract value per Miller Act requirements will be provided concurrent with the performance bond.",
             "missing_elements": [], "page_reference": 14},
        ],
        "Credentials": [
            {"status": "Complete", "confidence_score": 0.98, "percentage_filled": 100.0,
             "proposal_evidence": "License No. CGC-12345 valid through 12/2027. Copy included in Appendix B.",
             "missing_elements": [], "page_reference": 2},
            {"status": "Complete", "confidence_score": 0.93, "percentage_filled": 100.0,
             "proposal_evidence": "Founded in 2008, Titan Construction has 17 years of experience with 22 completed commercial projects exceeding $5M each.",
             "missing_elements": [], "page_reference": 3},
            {"status": "Partial", "confidence_score": 0.65, "percentage_filled": 40.0,
             "proposal_evidence": "John Smith, proposed Project Manager, has 12 years of experience managing large-scale commercial projects.",
             "missing_elements": ["PMP certification not mentioned", "Only 2 similar-scope projects listed, requirement is 3"], "page_reference": 8},
        ],
        "Environmental": [
            {"status": "Incomplete", "confidence_score": 0.88, "percentage_filled": 0.0,
             "proposal_evidence": None,
             "missing_elements": ["SWPPP plan not included in proposal", "NPDES permit compliance not addressed"], "page_reference": None},
            {"status": "Partial", "confidence_score": 0.70, "percentage_filled": 30.0,
             "proposal_evidence": "All waste materials will be disposed of in accordance with applicable regulations.",
             "missing_elements": ["Specific EPA 40 CFR Part 261 compliance not cited", "Hazardous waste disposal procedures not detailed"], "page_reference": 22},
        ],
        "Materials": [
            {"status": "Complete", "confidence_score": 0.96, "percentage_filled": 100.0,
             "proposal_evidence": "All concrete supplied by Ready-Mix Inc. will meet ASTM C94/C94M with minimum 4,000 PSI compressive strength verified at 28 days per specifications in Section 03300.",
             "missing_elements": [], "page_reference": 18},
            {"status": "Partial", "confidence_score": 0.72, "percentage_filled": 55.0,
             "proposal_evidence": "Structural steel will conform to ASTM A992 specifications.",
             "missing_elements": ["Buy America sourcing certification not provided", "ASTM A992M designation not explicitly referenced"], "page_reference": 19},
        ],
        "Timeline": [
            {"status": "Complete", "confidence_score": 0.94, "percentage_filled": 100.0,
             "proposal_evidence": "We commit to substantial completion within 16 months of Notice to Proceed, two months ahead of the 18-month requirement.",
             "missing_elements": [], "page_reference": 6},
            {"status": "Incomplete", "confidence_score": 0.85, "percentage_filled": 0.0,
             "proposal_evidence": None,
             "missing_elements": ["CPM schedule not included in proposal", "30-day submittal commitment not addressed", "Major milestones not identified"], "page_reference": None},
        ],
        "Staffing": [
            {"status": "Partial", "confidence_score": 0.78, "percentage_filled": 65.0,
             "proposal_evidence": "Resumes for John Smith (Project Manager) and Mike Johnson (Superintendent) are included in Appendix C.",
             "missing_elements": ["Quality Control Manager resume not provided"], "page_reference": 30},
        ],
        "Financial": [
            {"status": "Incomplete", "confidence_score": 0.92, "percentage_filled": 0.0,
             "proposal_evidence": None,
             "missing_elements": ["Audited financial statements not included", "Must provide 3 years of fiscal records"], "page_reference": None},
        ],
        "References": [
            {"status": "Partial", "confidence_score": 0.82, "percentage_filled": 60.0,
             "proposal_evidence": "References provided: City Hall Renovation (2022), Harbor Bridge Expansion (2023), Municipal Water Treatment Plant (2021).",
             "missing_elements": ["Only 3 references provided, 5 required", "Contact information incomplete for 1 reference"], "page_reference": 35},
        ],
        "Quality Control": [
            {"status": "Partial", "confidence_score": 0.68, "percentage_filled": 45.0,
             "proposal_evidence": "Our quality control program includes regular inspections and material testing per project specifications.",
             "missing_elements": ["USACE ER 1180-1-6 compliance not referenced", "Designated QC Manager not named"], "page_reference": 24},
        ],
        "Legal": [
            {"status": "Complete", "confidence_score": 0.97, "percentage_filled": 100.0,
             "proposal_evidence": "We hereby certify that Titan Construction LLC has not been debarred, suspended, or proposed for debarment from federal contracting. SAM.gov registration #ABCD1234.",
             "missing_elements": [], "page_reference": 40},
        ],
    }

    for req in requirements.requirements:
        category = req.category
        if category in mock_statuses and mock_statuses[category]:
            mock = mock_statuses[category].pop(0)
        else:
            mock = {
                "status": "Incomplete", "confidence_score": 0.85, "percentage_filled": 0.0,
                "proposal_evidence": None,
                "missing_elements": [f"No information found addressing: {req.requirement}"],
                "page_reference": None,
            }

        results.append(ComplianceObject(
            category=req.category,
            requirement=req.requirement,
            **mock,
        ))

    return AuditReport(proposal_id=proposal_id, rfp_name=rfp_name, audit_results=results)
