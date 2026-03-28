"""
Extractor Module — Extracts structured requirements from RFP text.

Hackathon: Uses Gemini via google-genai with structured JSON output.
Future: Docling layout-aware OCR → Vector DB embedding.
"""
import os
from google import genai
from .schema import RequirementList


# Maximum characters to send to the LLM in a single extraction call.
# Gemini 1.5/2.0 Flash supports very large contexts, but we chunk for reliability.
MAX_CONTEXT_CHARS = 120_000


def get_requirements(rfp_text: str) -> RequirementList:
    """
    Extracts mandatory requirements from RFP document text.

    Args:
        rfp_text: Full text extracted from the RFP PDF.

    Returns:
        RequirementList containing all identified requirements.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[Extractor] GEMINI_API_KEY not found — using mock data.")
        return _get_mock_requirements()

    try:
        client = genai.Client(api_key=api_key)

        # Truncate to fit context window if needed
        truncated = rfp_text[:MAX_CONTEXT_CHARS]

        prompt = f"""You are an expert civil engineer and procurement officer specializing in public sector RFP analysis.

Analyze the following RFP document and extract ALL mandatory requirements that a responding company must satisfy.

For each requirement:
- Assign a clear category (e.g., 'Safety', 'Insurance', 'Credentials', 'Environmental', 'Materials', 'Timeline', 'Bonding', 'Staffing', 'Equipment', 'Permits', 'Quality Control', 'Financial', 'Legal', 'References', 'Technical Specifications')
- Extract the exact requirement text. Be specific — include quantities, standards, certifications, and deadlines.

Focus on requirements related to:
1. Safety plans and OSHA compliance
2. Insurance and bonding requirements
3. Company credentials, certifications, and licenses
4. Risk management and mitigation plans
5. Environmental compliance
6. Staffing and key personnel qualifications
7. Equipment and materials specifications
8. Timeline and milestone requirements
9. Financial qualifications and bid bonds
10. References and past performance

RFP Document:
{truncated}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": RequirementList,
            },
        )
        result = RequirementList.model_validate_json(response.text)
        print(f"[Extractor] Extracted {len(result.requirements)} requirements via Gemini.")
        return result

    except Exception as e:
        print(f"[Extractor] LLM error: {e} — falling back to mock data.")
        return _get_mock_requirements()


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
