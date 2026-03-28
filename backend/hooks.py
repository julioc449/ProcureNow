"""
Expansion Hooks — Future-proofing stubs and active utilities.

Hook A: HistoryService — Compare against past wins (future: Vector DB).
Hook B: ImageProcessor — Vision-to-text for diagrams (future: Gemini Vision).
Hook C: export_to_csv — Active implementation for CSV export.
"""
import pandas as pd
from .schema import AuditReport


class HistoryService:
    """
    Hook A: Compare current audit against previous company wins.
    Future: Retrieve past winning proposals from Vector DB and compare ComplianceObject arrays.
    """
    def compare_against_past_wins(self, current_audit: AuditReport):
        print("[HistoryService] Hook called. Future: Vector DB retrieval of past wins.")
        return None


class ImageProcessor:
    """
    Hook B: Vision-to-Text for verifying required diagrams/charts are present.
    Future: Pass image chunks of the PDF to Gemini Vision to verify diagrams.
    """
    def verify_diagrams(self, proposal_pdf_path: str):
        print("[ImageProcessor] Hook called. Future: Vision-to-Text extraction.")
        return None


def export_to_csv(audit: AuditReport, output_path: str = "audit_report.csv") -> str:
    """
    Hook C: Export AuditReport to CSV for procurement officers.

    Returns:
        Path to the generated CSV file.
    """
    data = []
    for res in audit.audit_results:
        data.append({
            "Category": res.category,
            "Requirement": res.requirement,
            "Status": res.status,
            "Confidence": round(res.confidence_score, 2),
            "% Filled": round(res.percentage_filled, 1),
            "Evidence": res.proposal_evidence if res.proposal_evidence else "N/A",
            "Missing Elements": " | ".join(res.missing_elements) if res.missing_elements else "None",
            "Page": res.page_reference if res.page_reference else "N/A",
        })
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"[Hooks] Exported audit report to {output_path}")
    return output_path
