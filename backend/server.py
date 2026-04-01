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
import hashlib

from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .pdf_reader import ingest_pdf_multimodal, extract_text_from_bytes
from .extractor import get_requirements, extract_toc_and_page_map
from .auditor import audit_proposal
from .hooks import export_to_csv
from .reporter import generate_audit_report
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

        # ── Memoization Check ───────────────────────────────────────────────
        rfp_hash = hashlib.md5(rfp_bytes).hexdigest()
        cached_requirements = database.get_memoized_rubric(rfp_hash)

        if cached_requirements:
            print(f"\n[Pipeline] ⚡ CACHE HIT: Found memoized rubric for {rfp_name} ({rfp_hash})")
            print("[Pipeline] ⏭️ Skipping Phase 1 (RFP Ingestion) and Phase 2a (Requirement Extraction)")
            requirements = cached_requirements
            
            # Still need to ingest proposal
            print(f"\n[Pipeline] ═══ Phase 1: Multimodal PDF Ingestion (Proposal Only) ═══")
            print(f"[Pipeline] Ingesting Proposal: {proposal.filename} ({len(proposal_bytes):,} bytes)")
            proposal_content = ingest_pdf_multimodal(proposal_bytes, label="Proposal")
            
            print("\n[Pipeline] ═══ Phase 2b: Proposal TOC Mapping ═══")
            page_map = extract_toc_and_page_map(proposal_content)
            if page_map:
                print(f"[Pipeline] TOC sections: {list(page_map.keys())[:6]}{'...' if len(page_map) > 6 else ''}")
                
        else:
            print(f"\n[Pipeline] 🔍 CACHE MISS: No memoized rubric for {rfp_name} ({rfp_hash})")
            # ── Phase 1: Multimodal Ingestion ───────────────────────────────────
            print("\n[Pipeline] ═══ Phase 1: Multimodal PDF Ingestion ═══")
            print(f"[Pipeline] Ingesting RFP: {rfp_name} ({len(rfp_bytes):,} bytes)")
            rfp_content = ingest_pdf_multimodal(rfp_bytes, label="RFP")
            print(f"[Pipeline] Ingesting Proposal: {proposal.filename} ({len(proposal_bytes):,} bytes)")
            proposal_content = ingest_pdf_multimodal(proposal_bytes, label="Proposal")
    
            # ── Phase 2: Schema Generation + TOC Mapping ────────────────────────
            print("\n[Pipeline] ═══ Phase 2: RFP Rubric Extraction + TOC Mapping ═══")
            requirements = get_requirements(rfp_content)
            print(f"[Pipeline] Found {len(requirements.requirements)} requirements. Saving to cache.")
            database.save_memoized_rubric(rfp_hash, rfp_name, requirements)
    
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
        
        # Inject PDF bytes for persistence
        audit_report.rfp_pdf = rfp_bytes
        audit_report.proposal_pdf = proposal_bytes

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


class OverrideRequest(BaseModel):
    requirement: str
    status: str

@app.patch("/api/audits/{audit_id}/override")
async def override_audit_status(audit_id: str, payload: OverrideRequest):
    """Manually override a requirement status and recalculate summary metrics."""
    if payload.status not in ("Complete", "Partial", "Incomplete"):
        raise HTTPException(status_code=400, detail="Invalid status")
        
    success = database.update_requirement_status(audit_id, payload.requirement, payload.status)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update requirement status")
        
    return JSONResponse(content={"success": True})


@app.get("/api/export-pdf/{audit_id}")
async def download_pdf(audit_id: str):
    """Download a specific audit report as a branded PDF file."""
    audit = database.get_audit(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
        
    # Generate PDF (returns temp path)
    pdf_path = generate_audit_report(audit.summary_dict())
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"Compliance_Audit_{audit_id}.pdf"
    )


@app.get("/api/export-csv/{audit_id}")
async def download_csv(audit_id: str):
    """Download a specific audit report as a CSV file."""
    csv_path = _get_csv_path(audit_id)
    if not os.path.exists(csv_path):
        # If file doesn't exist, try to regenerate it from DB
        audit = database.get_audit(audit_id)
        if not audit:
            raise HTTPException(status_code=404, detail="Audit not found")
        export_to_csv(audit, csv_path)
        
    return FileResponse(
        csv_path,
        media_type="text/csv",
        filename=f"Compliance_Audit_{audit_id}.csv"
    )


@app.get("/api/audits/{audit_id}/pdf/{type}")
async def get_stored_pdf(audit_id: str, type: str):
    """Retrieve the original RFP or Proposal PDF from the database."""
    if type not in ["rfp", "proposal"]:
        raise HTTPException(status_code=400, detail="Invalid PDF type. Use 'rfp' or 'proposal'.")
        
    pdf_map = database.get_audit_pdfs(audit_id)
    pdf_bytes = pdf_map.get(type)
    
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail=f"No {type} PDF found for this audit.")
        
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={type}_{audit_id}.pdf"
        }
    )


# Serve the frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=True)
