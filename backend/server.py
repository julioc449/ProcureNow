"""
FastAPI Server — RFP Compliance Auditor API & Static File Server.

Endpoints:
  POST /api/full-audit  — Upload RFP + Proposal PDFs, run full pipeline, return AuditReport.
  GET  /api/export-csv   — Download the last audit as CSV.
  GET  /                 — Serve the frontend dashboard.
"""
import os
import tempfile
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .pdf_reader import extract_text_from_bytes
from .extractor import get_requirements
from .auditor import audit_proposal
from .hooks import export_to_csv

app = FastAPI(title="RFP Compliance Auditor", version="1.0.0")

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for the last audit (prototype simplicity)
_last_audit = None
_csv_path = None


@app.post("/api/full-audit")
async def full_audit(
    rfp: UploadFile = File(..., description="The RFP PDF document"),
    proposal: UploadFile = File(..., description="The submittal/proposal PDF document"),
):
    """
    Full pipeline: Extract text from both PDFs → Extract requirements from RFP →
    Audit proposal against requirements → Return structured AuditReport.
    """
    global _last_audit, _csv_path

    try:
        # 1. Read uploaded files
        rfp_bytes = await rfp.read()
        proposal_bytes = await proposal.read()

        # 2. Extract text from PDFs
        print("\n[Pipeline] Step 1: Extracting text from RFP PDF...")
        rfp_text = extract_text_from_bytes(rfp_bytes)
        print(f"[Pipeline] Extracted {len(rfp_text)} characters from RFP.")

        print("[Pipeline] Step 2: Extracting text from Proposal PDF...")
        proposal_text = extract_text_from_bytes(proposal_bytes)
        print(f"[Pipeline] Extracted {len(proposal_text)} characters from Proposal.")

        # 3. Extract requirements from the RFP
        print("[Pipeline] Step 3: Extracting requirements from RFP...")
        requirements = get_requirements(rfp_text)
        print(f"[Pipeline] Found {len(requirements.requirements)} requirements.")

        # 4. Audit the proposal against requirements
        proposal_id = f"AUDIT_{uuid.uuid4().hex[:8].upper()}"
        rfp_name = rfp.filename or "Uploaded RFP"

        print("[Pipeline] Step 4: Auditing proposal compliance...")
        audit_report = audit_proposal(
            proposal_text=proposal_text,
            requirements=requirements,
            proposal_id=proposal_id,
            rfp_name=rfp_name,
        )

        # 5. Store for CSV export
        _last_audit = audit_report
        _csv_path = os.path.join(tempfile.gettempdir(), f"{proposal_id}_audit.csv")
        export_to_csv(audit_report, _csv_path)

        print(f"[Pipeline] ✅ Audit complete: {audit_report.overall_percentage}% overall compliance.")

        return JSONResponse(content=audit_report.summary_dict())

    except Exception as e:
        print(f"[Pipeline] ❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/demo-audit")
async def demo_audit():
    """
    Run the audit pipeline with mock data (no PDFs needed).
    Useful for testing the dashboard without uploading files.
    """
    global _last_audit, _csv_path

    from .extractor import _get_mock_requirements
    from .auditor import _get_mock_audit

    requirements = _get_mock_requirements()
    proposal_id = f"DEMO_{uuid.uuid4().hex[:8].upper()}"
    audit_report = _get_mock_audit(requirements, proposal_id, "Demo RFP — City Hall Renovation")

    _last_audit = audit_report
    _csv_path = os.path.join(tempfile.gettempdir(), f"{proposal_id}_audit.csv")
    export_to_csv(audit_report, _csv_path)

    return JSONResponse(content=audit_report.summary_dict())


@app.get("/api/export-csv")
async def download_csv():
    """Download the last audit report as a CSV file."""
    if not _csv_path or not os.path.exists(_csv_path):
        raise HTTPException(status_code=404, detail="No audit report available. Run an audit first.")
    return FileResponse(
        _csv_path,
        media_type="text/csv",
        filename="compliance_audit_report.csv",
    )


# Serve the frontend static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=True)
