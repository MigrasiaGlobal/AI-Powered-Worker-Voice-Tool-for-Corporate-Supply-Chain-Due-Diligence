import json
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from .models import ChatSession
from .utils import get_company_policy_report


class PolicyReportPDF:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom styles for the PDF"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=HexColor('#2c3e50'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Header style
        self.styles.add(ParagraphStyle(
            name='CustomHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=HexColor('#34495e'),
            fontName='Helvetica-Bold'
        ))
        
        # Subheader style
        self.styles.add(ParagraphStyle(
            name='CustomSubHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=HexColor('#7f8c8d'),
            fontName='Helvetica-Bold'
        ))
        
        # Body text style
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        ))
        
        # Incident style
        self.styles.add(ParagraphStyle(
            name='IncidentStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leftIndent=20,
            fontName='Helvetica',
            textColor=HexColor('#e67e22')
        ))
        
        # Violation style
        self.styles.add(ParagraphStyle(
            name='ViolationStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=8,
            leftIndent=20,
            fontName='Helvetica',
            textColor=HexColor('#e74c3c')
        ))
        
        # Reference style
        self.styles.add(ParagraphStyle(
            name='ReferenceStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=6,
            leftIndent=30,
            fontName='Helvetica-Oblique',
            textColor=HexColor('#3498db')
        ))

    def create_header_footer(self, canvas, doc):
        """Create header and footer for each page"""
        canvas.saveState()
        
        # Header
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColor(HexColor('#2c3e50'))
        canvas.drawString(50, letter[1] - 50, "Supply Chain Policy Violation Report")
        
        # Footer
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(HexColor('#7f8c8d'))
        canvas.drawString(50, 30, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        canvas.drawRightString(letter[0] - 50, 30, f"Page {doc.page}")
        
        canvas.restoreState()

    def generate_session_report(self, session_id):
        """Generate PDF report for a specific session"""
        try:
            session = ChatSession.objects.get(id=session_id)
            violations = session.violations.all()
            
            # Create BytesIO buffer
            buffer = BytesIO()
            
            # Create PDF document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=100,
                bottomMargin=72
            )
            
            # Build story (content)
            story = []
            
            # Title
            title = Paragraph("Supply Chain Policy Violation Report", self.styles['CustomTitle'])
            story.append(title)
            story.append(Spacer(1, 20))
            
            # Session Information
            story.append(Paragraph("Session Information", self.styles['CustomHeader']))
            
            session_info = [
                ['Session ID:', str(session.id)],
                ['Factory Name:', session.factory_name or 'Not specified'],
                ['Location:', session.location or 'Not specified'],
                ['Language:', session.language or 'Not specified'],
                ['Created:', session.created_at.strftime('%Y-%m-%d %H:%M:%S')],
                ['Case Type:', session.case_type or 'Not specified']
            ]
            
            session_table = Table(session_info, colWidths=[2*inch, 4*inch])
            session_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 0), (-1, -1), black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(session_table)
            story.append(Spacer(1, 20))
            
            # Policy Violations
            if violations:
                story.append(Paragraph("Policy Violations", self.styles['CustomHeader']))
                
                for i, violation in enumerate(violations, 1):
                    # Violation header
                    story.append(Paragraph(f"Violation #{i} - {violation.buyer_company}", self.styles['CustomSubHeader']))
                    
                    # Complaint summary
                    if violation.complaint_summary:
                        story.append(Paragraph("<b>Complaint Summary:</b>", self.styles['CustomBody']))
                        story.append(Paragraph(violation.complaint_summary, self.styles['CustomBody']))
                        story.append(Spacer(1, 10))
                    
                    # Incidents
                    incidents_list = violation.get_incidents_list()
                    if incidents_list:
                        story.append(Paragraph("<b>Reported Incidents:</b>", self.styles['CustomBody']))
                        for incident in incidents_list:
                            story.append(Paragraph(f"• {incident}", self.styles['IncidentStyle']))
                        story.append(Spacer(1, 10))
                    
                    # Policy violations
                    violations_list = violation.get_violations_list()
                    if violations_list:
                        story.append(Paragraph("<b>Policy Violations Identified:</b>", self.styles['CustomBody']))
                        
                        for pv in violations_list:
                            # Violation description
                            story.append(Paragraph(f"<b>Category:</b> {pv.get('policy_category', 'Unknown')}", self.styles['ViolationStyle']))
                            story.append(Paragraph(f"<b>Incident:</b> {pv.get('incident', 'Not specified')}", self.styles['ViolationStyle']))
                            story.append(Paragraph(f"<b>Violation:</b> {pv.get('violation_description', 'Not specified')}", self.styles['ViolationStyle']))
                            
                            # Reference information
                            if 'reference' in pv:
                                ref = pv['reference']
                                story.append(Paragraph("<b>Policy Reference:</b>", self.styles['ReferenceStyle']))
                                story.append(Paragraph(f"Document: {ref.get('document_name', 'Unknown')}", self.styles['ReferenceStyle']))
                                story.append(Paragraph(f"Policy Content: {ref.get('policy_content', 'Not available')}", self.styles['ReferenceStyle']))
                                if ref.get('document_url') and ref['document_url'] != 'Not available':
                                    story.append(Paragraph(f"URL: {ref['document_url']}", self.styles['ReferenceStyle']))
                            
                            story.append(Spacer(1, 8))
                    
                    # If no structured data, show raw violation text
                    if not violation.complaint_summary and not incidents_list and not violations_list and violation.violation_text:
                        story.append(Paragraph("<b>Violation Details:</b>", self.styles['CustomBody']))
                        story.append(Paragraph(violation.violation_text, self.styles['CustomBody']))
                        story.append(Spacer(1, 10))
                    
                    # Add separator between violations
                    if i < len(violations):
                        story.append(Spacer(1, 15))
                        story.append(Paragraph("─" * 80, self.styles['CustomBody']))
                        story.append(Spacer(1, 15))
            else:
                story.append(Paragraph("No policy violations found for this session.", self.styles['CustomBody']))
            
            # Buyer Companies
            buyer_companies = session.buyer_companies.all()
            if buyer_companies:
                story.append(PageBreak())
                story.append(Paragraph("Associated Buyer Companies", self.styles['CustomHeader']))
                
                company_data = [['Company Name', 'Association Type']]
                for company in buyer_companies:
                    company_data.append([company.name, 'Supply Chain Partner'])
                
                company_table = Table(company_data, colWidths=[3*inch, 2*inch])
                company_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#3498db')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, HexColor('#bdc3c7')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                
                story.append(company_table)
            
            # Build PDF
            doc.build(story, onFirstPage=self.create_header_footer, onLaterPages=self.create_header_footer)
            
            # Get PDF data
            pdf_data = buffer.getvalue()
            buffer.close()
            
            return pdf_data
            
        except ChatSession.DoesNotExist:
            return None
        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            return None

    def create_http_response(self, pdf_data, filename):
        """Create HTTP response for PDF download"""
        if not pdf_data:
            return None
        
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


def generate_session_pdf(session_id):
    """Helper function to generate PDF for a session"""
    pdf_generator = PolicyReportPDF()
    pdf_data = pdf_generator.generate_session_report(session_id)
    
    if pdf_data:
        filename = f"policy_violation_report_session_{session_id}.pdf"
        return pdf_generator.create_http_response(pdf_data, filename)
    
    return None