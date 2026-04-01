import csv
from .schema import AuditReport


def export_to_csv(audit: AuditReport, output_path: str = "audit_report.csv") -> str:
    """
    Hook C: Export AuditReport to CSV for procurement officers.

    Returns:
        Path to the generated CSV file.
    """
    fieldnames = ["Category", "Requirement", "Status", "Confidence", "% Filled", "Evidence", "Missing Elements", "Page"]
    
    with open(output_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for res in audit.audit_results:
            writer.writerow({
                "Category": res.category,
                "Requirement": res.requirement,
                "Status": res.status,
                "Confidence": round(res.confidence_score, 2),
                "% Filled": round(res.percentage_filled, 1),
                "Evidence": res.proposal_evidence if res.proposal_evidence else "N/A",
                "Missing Elements": " | ".join(res.missing_elements) if res.missing_elements else "None",
                "Page": res.page_reference if res.page_reference else "N/A",
            })
            
    print(f"[Hooks] Exported audit report to {output_path}")
    return output_path
