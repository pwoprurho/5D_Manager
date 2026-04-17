from fpdf import FPDF
from datetime import datetime
from decimal import Decimal
import os

class ReportGenerator:
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=15)
        self.pdf.add_page()
        
        # Colors (Standardized with System)
        self.BRAND_RED = (227, 30, 36)
        self.NAVY_DEEP = (15, 23, 42)
        self.TEXT_DARK = (51, 65, 85)

    def generate_weekly_status(self, performance: dict, work_packages: list, site_updates: list) -> str:
        """Generates a professional 5D Status Report."""
        
        # Header
        self.pdf.set_fill_color(*self.NAVY_DEEP)
        self.pdf.rect(0, 0, 210, 40, 'F')
        
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.set_font("helvetica", "B", 24)
        self.pdf.text(15, 18, "OPERATIONAL_STATUS_REPORT")
        
        self.pdf.set_font("helvetica", "B", 10)
        self.pdf.set_text_color(*self.BRAND_RED)
        self.pdf.text(15, 28, f"PROJECT: {self.project_name.upper()}")
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.text(150, 28, f"TIMESTAMP: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")

        self.pdf.ln(45)

        # 1. Performance Overview (KPI Grid)
        self.pdf.set_font("helvetica", "B", 14)
        self.pdf.set_text_color(*self.NAVY_DEEP)
        self.pdf.cell(0, 10, "01 PERFORMANCE METRICS", 0, 1)
        self.pdf.set_draw_color(*self.BRAND_RED)
        self.pdf.line(10, self.pdf.get_y(), 200, self.pdf.get_y())
        self.pdf.ln(5)

        self.pdf.set_font("helvetica", "B", 10)
        self.pdf.cell(50, 10, "BAC (Budget At Completion):", 0, 0)
        self.pdf.set_font("helvetica", "", 10)
        self.pdf.cell(40, 10, f"NGN {performance['bac']:,.2f}", 0, 1)

        self.pdf.set_font("helvetica", "B", 10)
        self.pdf.cell(50, 10, "EAC (Est. At Completion):", 0, 0)
        self.pdf.set_font("helvetica", "", 10)
        self.pdf.cell(40, 10, f"NGN {performance['eac']:,.2f}", 0, 1)

        self.pdf.set_font("helvetica", "B", 10)
        self.pdf.cell(50, 10, "CPI (Efficiency Index):", 0, 0)
        self.pdf.set_font("helvetica", "B", 10)
        cpi = performance['cpi']
        if cpi < 1.0:
            self.pdf.set_text_color(*self.BRAND_RED)
        else:
            self.pdf.set_text_color(16, 185, 129) # Success Green
        self.pdf.cell(40, 10, f"{cpi:.2f}", 0, 1)
        self.pdf.set_text_color(*self.TEXT_DARK)

        self.pdf.ln(10)

        # 2. Critical Work Packages
        self.pdf.set_font("helvetica", "B", 14)
        self.pdf.set_text_color(*self.NAVY_DEEP)
        self.pdf.cell(0, 10, "02 PRODUCTION NODES", 0, 1)
        self.pdf.set_draw_color(*self.BRAND_RED)
        self.pdf.line(10, self.pdf.get_y(), 200, self.pdf.get_y())
        self.pdf.ln(5)

        self.pdf.set_font("helvetica", "B", 8)
        self.pdf.set_fill_color(241, 245, 249)
        self.pdf.cell(80, 8, "NODE NAME", 1, 0, 'C', True)
        self.pdf.cell(40, 8, "STATUS", 1, 0, 'C', True)
        self.pdf.cell(30, 8, "PROGRESS", 1, 0, 'C', True)
        self.pdf.cell(40, 8, "BUDGET (NGN)", 1, 1, 'C', True)

        self.pdf.set_font("helvetica", "", 8)
        for wp in work_packages[:15]: # Show first 15 tasks
            self.pdf.cell(80, 8, f" {wp['name'][:35]}", 1)
            self.pdf.cell(40, 8, f" {wp['status'].upper()}", 1)
            self.pdf.cell(30, 8, f" {wp['progress_pct']}%", 1, 0, 'C')
            self.pdf.cell(40, 8, f" {float(wp['budget_amount']):,.2f} ", 1, 1, 'R')

        self.pdf.ln(15)

        # 3. Field Telemetry (Site Updates)
        if site_updates:
            self.pdf.add_page()
            self.pdf.set_font("helvetica", "B", 14)
            self.pdf.set_text_color(*self.NAVY_DEEP)
            self.pdf.cell(0, 10, "03 FIELD TELEMETRY FEED", 0, 1)
            self.pdf.set_draw_color(*self.BRAND_RED)
            self.pdf.line(10, self.pdf.get_y(), 200, self.pdf.get_y())
            self.pdf.ln(5)

            for update in site_updates[:10]:
                self.pdf.set_font("helvetica", "B", 9)
                self.pdf.cell(0, 6, f"LOG_ID: {update['id']} | {update['timestamp'][:16]}", 0, 1)
                self.pdf.set_font("helvetica", "", 9)
                self.pdf.multi_cell(0, 5, f"NOTES: {update['notes'] or 'No description recorded.'}")
                if update.get('photo_url'):
                    # We would attempt to embed the image if reachable local path or Download first
                    self.pdf.cell(0, 5, "[PHOTO_EVIDENCE ATTACHED]", 0, 1)
                self.pdf.ln(3)

        # Save to temp path
        output_dir = os.path.join("static", "reports")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        filename = f"report_{self.project_name.lower().replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        filepath = os.path.join(output_dir, filename)
        self.pdf.output(filepath)
        
        return f"/static/reports/{filename}"

    def generate_requisition_pdf(self, request_data: dict, project: dict, material: dict, requester: dict) -> str:
        """Generates a formal Material Requisition Form."""
        
        # Header (Red Stripe)
        self.pdf.set_fill_color(*self.BRAND_RED)
        self.pdf.rect(0, 0, 210, 30, 'F')
        
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.set_font("helvetica", "B", 18)
        self.pdf.text(15, 15, "MATERIAL_REQUISITION_FORM")
        
        self.pdf.set_font("helvetica", "B", 8)
        self.pdf.text(15, 22, f"REQ_ID: {request_data['id']} | DISPATCH_PROTOCOL_V12")
        self.pdf.text(150, 22, f"DATE: {request_data['request_date'][:10]}")

        self.pdf.ln(35)

        # 1. Project Context
        self.pdf.set_font("helvetica", "B", 12)
        self.pdf.set_text_color(*self.NAVY_DEEP)
        self.pdf.cell(0, 10, "01 PROJECT INFORMATION", 0, 1)
        self.pdf.set_draw_color(*self.BRAND_RED)
        self.pdf.line(10, self.pdf.get_y(), 200, self.pdf.get_y())
        self.pdf.ln(5)

        self.pdf.set_font("helvetica", "B", 10)
        self.pdf.cell(40, 8, "Project Name:", 0, 0)
        self.pdf.set_font("helvetica", "", 10)
        self.pdf.cell(0, 8, project['name'].upper(), 0, 1)

        self.pdf.set_font("helvetica", "B", 10)
        self.pdf.cell(40, 8, "Requester:", 0, 0)
        self.pdf.set_font("helvetica", "", 10)
        self.pdf.cell(0, 8, f"{requester['username']} ({requester['role'].upper()})", 0, 1)

        self.pdf.ln(10)

        # 2. Resource Specifications
        self.pdf.set_font("helvetica", "B", 12)
        self.pdf.cell(0, 10, "02 RESOURCE SPECIFICATIONS", 0, 1)
        self.pdf.line(10, self.pdf.get_y(), 200, self.pdf.get_y())
        self.pdf.ln(5)

        # Table Header
        self.pdf.set_font("helvetica", "B", 10)
        self.pdf.set_fill_color(241, 245, 249)
        self.pdf.cell(80, 10, "MATERIAL DESCRIPTION", 1, 0, 'C', True)
        self.pdf.cell(30, 10, "UNIT", 1, 0, 'C', True)
        self.pdf.cell(40, 10, "QTY REQUESTED", 1, 0, 'C', True)
        self.pdf.cell(40, 10, "STATUS", 1, 1, 'C', True)

        # Table Data
        self.pdf.set_font("helvetica", "", 10)
        self.pdf.cell(80, 12, f" {material['name'].upper()}", 1)
        self.pdf.cell(30, 12, f" {material['unit'].upper()}", 1, 0, 'C')
        self.pdf.cell(40, 12, f" {request_data['quantity_requested']}", 1, 0, 'C')
        self.pdf.cell(40, 12, f" {request_data['status'].upper()}", 1, 1, 'C')

        self.pdf.ln(20)

        # 3. Authorization Signatures
        self.pdf.set_font("helvetica", "B", 12)
        self.pdf.cell(0, 10, "03 LOGISTICS AUTHORIZATION", 0, 1)
        self.pdf.line(10, self.pdf.get_y(), 200, self.pdf.get_y())
        self.pdf.ln(15)

        y_sig = self.pdf.get_y()
        self.pdf.line(15, y_sig, 75, y_sig)
        self.pdf.line(115, y_sig, 175, y_sig)

        self.pdf.set_font("helvetica", "I", 8)
        self.pdf.text(15, y_sig + 5, "REQUESTED BY (PROJECT MANAGER)")
        self.pdf.text(115, y_sig + 5, "AUTHORIZED BY (DIRECTOR/ADMIN)")

        self.pdf.ln(20)
        self.pdf.set_font("helvetica", "B", 7)
        self.pdf.set_text_color(150, 150, 150)
        self.pdf.multi_cell(0, 4, "NOTICE: This is an automatically generated site document from the Vinicius Command System. "
                               "Electronic authorization is verified. Physical signature is required for site dispatch logs.", align='C')

        # Save
        output_dir = os.path.join("static", "reports")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        filename = f"requisition_{request_data['id']}_{datetime.utcnow().strftime('%H%M%S')}.pdf"
        filepath = os.path.join(output_dir, filename)
        self.pdf.output(filepath)
        
        return f"/static/reports/{filename}"
