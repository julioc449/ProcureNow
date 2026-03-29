"""
FastAPI Server — RFP Compliance Auditor API & Static File Server.

4-Phase Multimodal Pipeline:
  Phase 1: Multimodal PDF ingestion via Gemini File Upload API (tables, charts, grids)
  Phase 2: Dynamic RFP rubric extraction + Proposal TOC/page-map
  Phase 3: Section-routed cross-verification with Presence/Accuracy/Context evaluation
  Phase 4: Structured AuditReport output with critical omissions

Endpoints:
  POST /api/full-audit  — Upload RFP + Proposal PDFs, run pipeline, return AuditReport.
  POST /api/demo-audit  — Run with mock data (no PDFs needed).
  GET  /api/export-csv  — Download last audit as CSV.
  GET  /               — Serve frontend dashboard.
"""
import os
import tempfile
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .pdf_reader import ingest_pdf_multimodal, extract_text_from_bytes
from .extractor import get_requirements, extract_toc_and_page_map
from .auditor import audit_proposal
from .hooks import export_to_csv
from . import database

app = FastAPI(title="ProcureNow — RFP Compliance Auditor", version="2.0.0")

@app.on_event("startup")
def startup_event():
    database.init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper to get temp CSV path
def _get_csv_path(audit_id: str) -> str:
    return os.path.join(tempfile.gettempdir(), f"{audit_id}_audit.csv")


@app.post("/api/full-audit")
async def full_audit(
    rfp: UploadFile = File(..., description="The RFP PDF document"),
    proposal: UploadFile = File(..., description="The submittal/proposal PDF document"),
):
    """
    Full 4-phase multimodal pipeline:
    Phase 1 → Gemini vision ingestion of both PDFs (preserves tables & charts)
    Phase 2 → RFP rubric extraction + Proposal TOC page-map
    Phase 3 → Section-routed compliance cross-verification
    Phase 4 → Structured AuditReport JSON response
    """
    try:
        rfp_bytes = await rfp.read()
        proposal_bytes = await proposal.read()

        rfp_name = rfp.filename or "Uploaded RFP"
        proposal_id = f"AUDIT_{uuid.uuid4().hex[:8].upper()}"

        # ── Phase 1: Multimodal Ingestion ───────────────────────────────────
        print("\n[Pipeline] ═══ Phase 1: Multimodal PDF Ingestion ═══")
        print(f"[Pipeline] Ingesting RFP: {rfp_name} ({len(rfp_bytes):,} bytes)")
        rfp_content = ingest_pdf_multimodal(rfp_bytes, label="RFP")
        print(f"[Pipeline] Ingesting Proposal: {proposal.filename} ({len(proposal_bytes):,} bytes)")
        proposal_content = ingest_pdf_multimodal(proposal_bytes, label="Proposal")

        # ── Phase 2: Schema Generation + TOC Mapping ────────────────────────
        print("\n[Pipeline] ═══ Phase 2: RFP Rubric Extraction + TOC Mapping ═══")
        requirements = get_requirements(rfp_content)
        print(f"[Pipeline] Found {len(requirements.requirements)} requirements.")
        page_map = extract_toc_and_page_map(proposal_content)
        if page_map:
            print(f"[Pipeline] TOC sections: {list(page_map.keys())[:6]}{'...' if len(page_map) > 6 else ''}")

        # ── Phase 3: Semantic Routing & Cross-Verification ──────────────────
        print("\n[Pipeline] ═══ Phase 3: Section-Routed Compliance Audit ═══")
        audit_report = audit_proposal(
            proposal_text=proposal_content,
            requirements=requirements,
            proposal_id=proposal_id,
            rfp_name=rfp_name,
            page_map=page_map,
        )

        # ── Phase 4: Output ──────────────────────────────────────────────────
        database.save_audit(audit_report)
        export_to_csv(audit_report, _get_csv_path(proposal_id))
        
        print(f"\n[Pipeline] ✅ Audit complete — {audit_report.overall_percentage}% overall compliance.")
        return JSONResponse(content=audit_report.summary_dict())

    except Exception as e:
        import traceback
        print(f"[Pipeline] ❌ Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/demo-audit")
async def demo_audit():
    """Run the pipeline with mock data — no PDFs or API key needed."""
    from .extractor import _get_mock_requirements
    from .auditor import _get_mock_audit

    requirements = _get_mock_requirements()
    proposal_id = f"DEMO_{uuid.uuid4().hex[:8].upper()}"
    audit_report = _get_mock_audit(requirements, proposal_id, "Demo RFP — City Hall Renovation")

    database.save_audit(audit_report)
    export_to_csv(audit_report, _get_csv_path(proposal_id))

    return JSONResponse(content=audit_report.summary_dict())


@app.get("/api/audits")
async def list_audits(limit: int = 50, offset: int = 0):
    """List stored audits."""
    return JSONResponse(content=database.list_audits(limit, offset))


@app.get("/api/audits/{audit_id}")
async def get_audit(audit_id: str):
    """Retrieve a specific audit report."""
    audit = database.get_audit(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return JSONResponse(content=audit.summary_dict())


@app.delete("/api/audits/{audit_id}")
async def delete_audit(audit_id: str):
    """Delete a specific audit report."""
    deleted = database.delete_audit(audit_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Audit not found")
    return JSONResponse(content={"success": True})


@app.get("/api/export-csv/{audit_id}")
async def download_csv(audit_id: str):
    """Download a specific audit report as a CSV file."""
    csv_path = _get_csv_path(audit_id)
    
    # If the file doesn't exist locally (server restart etc), generate it
    if not os.path.exists(csv_path):
        audit = database.get_audit(audit_id)
        if not audit:
            raise HTTPException(status_code=404, detail="Audit not found")
        export_to_csv(audit, csv_path)
        
    return FileResponse(
        csv_path,
        media_type="text/csv",
        filename=f"compliance_audit_{audit_id}.csv",
    )


# Serve the frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=True)
