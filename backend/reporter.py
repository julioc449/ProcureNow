from fpdf import FPDF
from datetime import datetime
import os

class AuditPDF(FPDF):
    def __init__(self, rfp_name, proposal_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rfp_name = self._sanitize(rfp_name)
        self.proposal_id = proposal_id
        self.logo_path = "logo_procurenow.png"
        self.primary_color = (0, 71, 49)  # Deep Green from logo
        self.secondary_color = (184, 153, 94) # Gold from logo
        self.accent_color = (245, 247, 245) # Ivory background

    def _sanitize(self, text):
        if not text:
            return ""
        # Replace common non-Latin1 characters that cause Helvetica to crash
        return text.replace("—", "-").replace("–", "-").replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')

    def cell(self, w, h=0, txt="", *args, **kwargs):
        return super().cell(w, h, self._sanitize(txt), *args, **kwargs)

    def multi_cell(self, w, h=0, txt="", *args, **kwargs):
        return super().multi_cell(w, h, self._sanitize(txt), *args, **kwargs)

    def header(self):
        # Background color for header
        self.set_fill_color(*self.primary_color)
        self.rect(0, 0, 210, 40, 'F')
        
        # Logo
        if os.path.exists(self.logo_path):
            try:
                # Top left logo placement
                self.image(self.logo_path, 10, 8, 35)
            except:
                pass

        # Title
        self.set_font("helvetica", "B", 20)
        self.set_text_color(255, 255, 255)
        self.set_xy(50, 10)
        self.cell(0, 10, "Compliance Audit Report", ln=True)
        
        # Subtitle
        self.set_font("helvetica", "", 10)
        self.set_xy(50, 20)
        self.cell(0, 5, f"RFP: {self.rfp_name}", ln=True)
        self.set_xy(50, 25)
        self.cell(0, 5, f"Proposal ID: {self.proposal_id} | Issued: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
        
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"ProcureNow Internal Audit - Page {self.page_no()}/{{nb}}", align="C")

    def section_header(self, title):
        self.set_font("helvetica", "B", 14)
        self.set_text_color(*self.primary_color)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 10, f"  {title}", ln=True, fill=True)
        self.ln(4)

    def add_compliance_item(self, item):
        # Color coding based on status
        status = item.get("status", "Incomplete")
        if status == "Complete":
            color = (40, 167, 69) # Green
        elif status == "Partial":
            color = (255, 193, 7) # Yellow
        else:
            color = (220, 53, 69) # Red

        # Card Frame
        self.set_draw_color(200, 200, 200)
        self.set_fill_color(255, 255, 255)
        
        # Requirement Text
        self.set_font("helvetica", "B", 10)
        self.set_text_color(50, 50, 50)
        req_text = item.get('requirement', 'No Text')
        self.multi_cell(0, 6, req_text, border='TLR')
        
        # Status Bar
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self.set_font("helvetica", "B", 8)
        self.cell(40, 6, f"  STATUS: {status.upper()}", fill=True, border='L')
        
        self.set_fill_color(245, 245, 245)
        self.set_text_color(100, 100, 100)
        conf = int(item.get('confidence_score', 0) * 100)
        match = int(item.get('percentage_filled', 0))
        self.cell(60, 6, f"  AI CONFIDENCE: {conf}%", fill=True)
        self.cell(0, 6, f"  MATCH ACCURACY: {match}%", fill=True, border='R', ln=True)
        
        # Evidence / Missing
        self.set_font("helvetica", "", 9)
        self.set_text_color(80, 80, 80)
        evidence = item.get('proposal_evidence', 'No evidence provided.')
        page = item.get('page_reference')
        if page:
            evidence = f"[Page {page}] {evidence}"
            
        self.multi_cell(0, 5, f"Evidence: {evidence}", border='LRB')
        self.ln(5)

def generate_audit_report(data: dict) -> str:
    """
    Main entry point to generate a PDF from audit data.
    Returns the path to the temporary PDF file.
    """
    rfp_name = data.get("rfp_name", "Unknown RFP").replace("—", "-").replace("–", "-")
    proposal_id = data.get("proposal_id", "Unknown")
    results = data.get("audit_results", [])
    
    pdf = AuditPDF(rfp_name, proposal_id)
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Summary Statistics
    pdf.section_header("Executive Summary")
    pdf.set_font("helvetica", "", 11)
    passed = sum(1 for r in results if r.get('status') == 'Complete')
    partial = sum(1 for r in results if r.get('status') == 'Partial')
    failed = sum(1 for r in results if r.get('status') == 'Incomplete')
    
    pdf.cell(0, 8, f"Total Requirements Evaluated: {len(results)}", ln=True)
    pdf.set_text_color(40, 167, 69)
    pdf.cell(0, 8, f"Full Compliance: {passed}", ln=True)
    pdf.set_text_color(255, 193, 7)
    pdf.cell(0, 8, f"Partial Compliance: {partial}", ln=True)
    pdf.set_text_color(220, 53, 69)
    pdf.cell(0, 8, f"Non-Compliant: {failed}", ln=True)
    
    pdf.ln(10)
    
    # Detailed Findings
    # Group results by category
    categories = {}
    for r in results:
        cat = r.get('category', 'General')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)
        
    for cat, items in categories.items():
        if pdf.get_y() > 250: # Trigger page break
            pdf.add_page()
        pdf.section_header(cat)
        for item in items:
            if pdf.get_y() > 240:
                pdf.add_page()
            pdf.add_compliance_item(item)
            
    output_path = f"/tmp/Audit_Report_{proposal_id}.pdf"
    pdf.output(output_path)
    return output_path
