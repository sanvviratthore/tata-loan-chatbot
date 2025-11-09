"""
Document Agent

Generates professional PDF documents for loan offers, consolidation reports,
and credit improvement plans using ReportLab.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from io import BytesIO

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas

from agents.base_agent import BaseAgent, handle_errors, ValidationError
from schemas.models import LoanOffer, ConsolidationOffer, Customer
from utils.loan_calculator import generate_amortization_schedule


class DocumentAgent(BaseAgent):
    """
    Agent responsible for generating PDF documents for loan offers,
    consolidation reports, and credit improvement plans.
    """
    
    def __init__(self):
        """Initialize document agent."""
        super().__init__("document_agent")
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles for PDF generation."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#283593'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Highlight style
        self.styles.add(ParagraphStyle(
            name='Highlight',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1b5e20'),
            fontName='Helvetica-Bold'
        ))
    
    @handle_errors
    def process(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method for document generation.
        
        Args:
            input_data: Contains document_type and relevant data
            session_state: Current session state
        
        Returns:
            Response with PDF bytes and metadata
        """
        self.validate_input(input_data)
        
        document_type = input_data.get("document_type")
        
        self.log_action("generate_document", document_type=document_type)
        
        if document_type == "loan_offer":
            pdf_bytes = self.generate_offer_letter(
                input_data.get("offer"),
                input_data.get("customer")
            )
            filename = f"loan_offer_{input_data['offer']['offer_id']}.pdf"
        
        elif document_type == "consolidation_report":
            pdf_bytes = self.generate_consolidation_report(
                input_data.get("consolidation_offer"),
                input_data.get("customer")
            )
            filename = f"consolidation_report_{input_data['consolidation_offer']['offer_id']}.pdf"
        
        elif document_type == "credit_improvement_plan":
            pdf_bytes = self.generate_credit_improvement_plan(
                input_data.get("improvement_plan"),
                input_data.get("customer")
            )
            filename = f"credit_improvement_plan_{input_data['customer']['customer_id']}.pdf"
        
        else:
            raise ValidationError(f"Unknown document type: {document_type}")
        
        self.log_action("document_generated", 
                       document_type=document_type,
                       size_bytes=len(pdf_bytes))
        
        return self.create_response(
            success=True,
            data={
                "pdf_bytes": pdf_bytes,
                "filename": filename,
                "size_bytes": len(pdf_bytes),
                "document_type": document_type
            },
            message=f"Document generated successfully: {filename}"
        )
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for document generation.
        
        Args:
            input_data: Input data to validate
        
        Returns:
            True if validation passes
        
        Raises:
            ValidationError: If validation fails
        """
        if "document_type" not in input_data:
            raise ValidationError("document_type is required")
        
        document_type = input_data["document_type"]
        
        if document_type == "loan_offer":
            if "offer" not in input_data or "customer" not in input_data:
                raise ValidationError("offer and customer data required for loan offer letter")
        
        elif document_type == "consolidation_report":
            if "consolidation_offer" not in input_data or "customer" not in input_data:
                raise ValidationError("consolidation_offer and customer data required")
        
        elif document_type == "credit_improvement_plan":
            if "improvement_plan" not in input_data or "customer" not in input_data:
                raise ValidationError("improvement_plan and customer data required")
        
        else:
            raise ValidationError(f"Invalid document_type: {document_type}")
        
        return True

    
    def generate_offer_letter(self, offer: Dict[str, Any], customer: Dict[str, Any]) -> bytes:
        """
        Generate professional PDF loan offer letter.
        
        Args:
            offer: Loan offer details
            customer: Customer information
        
        Returns:
            PDF document as bytes
        """
        self.log_action("generating_offer_letter", offer_id=offer.get("offer_id"))
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        story = []
        
        # Header
        story.append(Paragraph("TATA CAPITAL", self.styles['CustomTitle']))
        story.append(Paragraph("Personal Loan Offer Letter", self.styles['CustomSubtitle']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Date and Offer ID
        date_str = datetime.now().strftime("%B %d, %Y")
        story.append(Paragraph(f"<b>Date:</b> {date_str}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Offer ID:</b> {offer['offer_id']}", self.styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))
        
        # Customer Details
        story.append(Paragraph("Customer Details", self.styles['CustomSubtitle']))
        customer_data = [
            ["Name:", customer['name']],
            ["Customer ID:", customer['customer_id']],
            ["PAN:", customer['pan']],
            ["Mobile:", customer['mobile']],
        ]
        if customer.get('email'):
            customer_data.append(["Email:", customer['email']])
        
        customer_table = Table(customer_data, colWidths=[2*inch, 4*inch])
        customer_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(customer_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Loan Offer Summary
        story.append(Paragraph("Loan Offer Summary", self.styles['CustomSubtitle']))
        
        offer_data = [
            ["Loan Amount:", f"₹ {offer['loan_amount']:,.2f}"],
            ["Interest Rate:", f"{offer['interest_rate']}% per annum"],
            ["Tenure:", f"{offer['tenure_months']} months"],
            ["Monthly EMI:", f"₹ {offer['monthly_emi']:,.2f}"],
            ["Processing Fee:", f"₹ {offer.get('processing_fee', 0):,.2f}"],
            ["Total Interest:", f"₹ {offer['total_interest']:,.2f}"],
            ["Total Repayment:", f"₹ {offer['total_repayment']:,.2f}"],
        ]
        
        offer_table = Table(offer_data, colWidths=[2.5*inch, 3.5*inch])
        offer_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e3f2fd')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#c8e6c9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(offer_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Offer Validity
        if offer.get('offer_valid_until'):
            story.append(Paragraph(
                f"<b>Offer Valid Until:</b> {offer['offer_valid_until']}",
                self.styles['Highlight']
            ))
            story.append(Spacer(1, 0.2 * inch))
        
        # Repayment Schedule
        story.append(Paragraph("Repayment Schedule (First 12 Months)", self.styles['CustomSubtitle']))
        schedule = generate_amortization_schedule(
            offer['loan_amount'],
            offer['interest_rate'],
            offer['tenure_months'],
            offer['monthly_emi']
        )
        
        schedule_data = [["Month", "Opening Balance", "EMI", "Interest", "Principal", "Closing Balance"]]
        for entry in schedule[:12]:  # First 12 months
            schedule_data.append([
                str(entry['month']),
                f"₹ {entry['opening_balance']:,.0f}",
                f"₹ {entry['emi']:,.0f}",
                f"₹ {entry['interest']:,.0f}",
                f"₹ {entry['principal']:,.0f}",
                f"₹ {entry['closing_balance']:,.0f}"
            ])
        
        schedule_table = Table(schedule_data, colWidths=[0.6*inch, 1.3*inch, 1*inch, 1*inch, 1*inch, 1.3*inch])
        schedule_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        story.append(schedule_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Special Conditions
        if offer.get('special_conditions'):
            story.append(Paragraph("Special Conditions", self.styles['CustomSubtitle']))
            for condition in offer['special_conditions']:
                story.append(Paragraph(f"• {condition}", self.styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))
        
        # Terms and Conditions
        story.append(Paragraph("Terms and Conditions", self.styles['CustomSubtitle']))
        terms = [
            "This offer is subject to credit approval and verification of documents.",
            "Interest rate is fixed for the entire tenure of the loan.",
            "Pre-payment charges may apply as per the loan agreement.",
            "Processing fee is non-refundable and will be deducted from the loan amount.",
            "Late payment charges will be applicable for delayed EMI payments.",
            "The loan is subject to terms and conditions as per the loan agreement."
        ]
        for term in terms:
            story.append(Paragraph(f"• {term}", self.styles['Normal']))
        
        story.append(Spacer(1, 0.3 * inch))
        
        # Footer
        story.append(Paragraph(
            "<i>For any queries, please contact us at support@tatacapital.com or call 1800-123-4567</i>",
            self.styles['Normal']
        ))
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes

    
    def generate_consolidation_report(self, consolidation_offer: Dict[str, Any], 
                                     customer: Dict[str, Any]) -> bytes:
        """
        Generate PDF consolidation comparison report.
        
        Args:
            consolidation_offer: Consolidation offer details
            customer: Customer information
        
        Returns:
            PDF document as bytes
        """
        self.log_action("generating_consolidation_report", 
                       offer_id=consolidation_offer.get("offer_id"))
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        story = []
        
        # Header
        story.append(Paragraph("TATA CAPITAL", self.styles['CustomTitle']))
        story.append(Paragraph("Debt Consolidation Report", self.styles['CustomSubtitle']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Date and Offer ID
        date_str = datetime.now().strftime("%B %d, %Y")
        story.append(Paragraph(f"<b>Date:</b> {date_str}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Offer ID:</b> {consolidation_offer['offer_id']}", self.styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))
        
        # Customer Details
        story.append(Paragraph(f"<b>Customer:</b> {customer['name']} ({customer['customer_id']})", 
                             self.styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Savings Highlight
        story.append(Paragraph("Your Savings with Consolidation", self.styles['CustomSubtitle']))
        
        savings_data = [
            ["Current Total EMI:", f"₹ {consolidation_offer['current_total_emi']:,.2f}"],
            ["New Consolidated EMI:", f"₹ {consolidation_offer['new_monthly_emi']:,.2f}"],
            ["Monthly Savings:", f"₹ {consolidation_offer['monthly_savings']:,.2f}"],
            ["Total Interest Savings:", f"₹ {consolidation_offer['total_interest_savings']:,.2f}"],
        ]
        
        savings_table = Table(savings_data, colWidths=[3*inch, 3*inch])
        savings_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#c8e6c9')),
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#a5d6a7')),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        story.append(savings_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Current Loans Summary
        story.append(Paragraph("Current Loans Being Consolidated", self.styles['CustomSubtitle']))
        
        current_loans_data = [["Loan Type", "Lender", "Outstanding", "Interest Rate", "Monthly EMI"]]
        for loan in consolidation_offer['loans_being_consolidated']:
            current_loans_data.append([
                loan['loan_type'],
                loan.get('lender', 'N/A'),
                f"₹ {loan['outstanding']:,.0f}",
                f"{loan['interest_rate']}%",
                f"₹ {loan['monthly_emi']:,.0f}"
            ])
        
        # Add total row
        total_outstanding = sum(loan['outstanding'] for loan in consolidation_offer['loans_being_consolidated'])
        current_loans_data.append([
            "TOTAL", "", 
            f"₹ {total_outstanding:,.0f}", 
            "", 
            f"₹ {consolidation_offer['current_total_emi']:,.0f}"
        ])
        
        current_loans_table = Table(current_loans_data, colWidths=[1.5*inch, 1.5*inch, 1.3*inch, 1*inch, 1.2*inch])
        current_loans_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ef5350')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ffcdd2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        story.append(current_loans_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # New Consolidated Loan
        story.append(Paragraph("New Consolidated Loan", self.styles['CustomSubtitle']))
        
        new_loan_data = [
            ["Consolidated Amount:", f"₹ {consolidation_offer['consolidated_amount']:,.2f}"],
            ["Interest Rate:", f"{consolidation_offer['new_interest_rate']}% per annum"],
            ["Tenure:", f"{consolidation_offer['new_tenure_months']} months"],
            ["Monthly EMI:", f"₹ {consolidation_offer['new_monthly_emi']:,.2f}"],
        ]
        
        new_loan_table = Table(new_loan_data, colWidths=[3*inch, 3*inch])
        new_loan_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f5e9')),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        story.append(new_loan_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Side-by-Side Comparison
        story.append(Paragraph("Comparison: Current vs Consolidated", self.styles['CustomSubtitle']))
        
        comparison_data = [
            ["", "Current Loans", "Consolidated Loan"],
            ["Number of Loans", str(len(consolidation_offer['loans_being_consolidated'])), "1"],
            ["Total Outstanding", f"₹ {total_outstanding:,.0f}", 
             f"₹ {consolidation_offer['consolidated_amount']:,.0f}"],
            ["Monthly EMI", f"₹ {consolidation_offer['current_total_emi']:,.0f}", 
             f"₹ {consolidation_offer['new_monthly_emi']:,.0f}"],
            ["Interest Rate", "Varies", f"{consolidation_offer['new_interest_rate']}%"],
        ]
        
        comparison_table = Table(comparison_data, colWidths=[2.5*inch, 2*inch, 2*inch])
        comparison_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#ffebee')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#e8f5e9')),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(comparison_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Benefits
        story.append(Paragraph("Benefits of Consolidation", self.styles['CustomSubtitle']))
        benefits = [
            f"Save ₹ {consolidation_offer['monthly_savings']:,.2f} every month",
            f"Reduce total interest by ₹ {consolidation_offer['total_interest_savings']:,.2f}",
            "Manage just one EMI instead of multiple payments",
            "Lower interest rate compared to current average",
            "Simplified loan management and tracking"
        ]
        for benefit in benefits:
            story.append(Paragraph(f"✓ {benefit}", self.styles['Normal']))
        
        story.append(Spacer(1, 0.3 * inch))
        
        # Footer
        story.append(Paragraph(
            "<i>This is an indicative offer. Final terms subject to credit approval and documentation.</i>",
            self.styles['Normal']
        ))
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes

    
    def generate_credit_improvement_plan(self, improvement_plan: Dict[str, Any], 
                                        customer: Dict[str, Any]) -> bytes:
        """
        Generate PDF credit improvement plan with actionable recommendations.
        
        Args:
            improvement_plan: Credit improvement plan details
            customer: Customer information
        
        Returns:
            PDF document as bytes
        """
        self.log_action("generating_credit_improvement_plan", 
                       customer_id=customer.get("customer_id"))
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        story = []
        
        # Header
        story.append(Paragraph("TATA CAPITAL", self.styles['CustomTitle']))
        story.append(Paragraph("Credit Improvement Plan", self.styles['CustomSubtitle']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Date
        date_str = datetime.now().strftime("%B %d, %Y")
        story.append(Paragraph(f"<b>Date:</b> {date_str}", self.styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))
        
        # Customer Details
        story.append(Paragraph(f"<b>Customer:</b> {customer['name']}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Customer ID:</b> {customer['customer_id']}", self.styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Current Status
        story.append(Paragraph("Current Credit Status", self.styles['CustomSubtitle']))
        
        current_score = improvement_plan.get('current_credit_score', 'N/A')
        target_score = improvement_plan.get('target_credit_score', 750)
        
        status_data = [
            ["Current Credit Score:", str(current_score)],
            ["Target Credit Score:", str(target_score)],
            ["Estimated Timeline:", improvement_plan.get('timeline', '6-12 months')],
        ]
        
        status_table = Table(status_data, colWidths=[3*inch, 3*inch])
        status_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ffebee')),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e8f5e9')),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        story.append(status_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Key Issues
        if improvement_plan.get('issues'):
            story.append(Paragraph("Key Issues Identified", self.styles['CustomSubtitle']))
            for issue in improvement_plan['issues']:
                story.append(Paragraph(f"• {issue}", self.styles['Normal']))
            story.append(Spacer(1, 0.3 * inch))
        
        # Action Plan
        story.append(Paragraph("Your Action Plan", self.styles['CustomSubtitle']))
        
        recommendations = improvement_plan.get('recommendations', [])
        if not recommendations:
            # Default recommendations if none provided
            recommendations = [
                {
                    "step": 1,
                    "action": "Pay all EMIs on time",
                    "description": "Set up auto-debit for all loan EMIs to ensure timely payments. Payment history accounts for 35% of your credit score.",
                    "timeline": "Immediate - Ongoing",
                    "impact": "High"
                },
                {
                    "step": 2,
                    "action": "Reduce credit utilization",
                    "description": "Keep credit card utilization below 30% of the limit. Pay off high-balance cards first.",
                    "timeline": "1-3 months",
                    "impact": "High"
                },
                {
                    "step": 3,
                    "action": "Avoid new credit inquiries",
                    "description": "Don't apply for new loans or credit cards for the next 6 months. Multiple inquiries can lower your score.",
                    "timeline": "6 months",
                    "impact": "Medium"
                },
                {
                    "step": 4,
                    "action": "Check credit report for errors",
                    "description": "Review your credit report from CIBIL, Experian, or Equifax. Dispute any errors or inaccuracies.",
                    "timeline": "1 month",
                    "impact": "Medium"
                },
                {
                    "step": 5,
                    "action": "Maintain old credit accounts",
                    "description": "Keep your oldest credit cards active. Length of credit history contributes to your score.",
                    "timeline": "Ongoing",
                    "impact": "Low"
                }
            ]
        
        for rec in recommendations:
            # Step header
            story.append(Paragraph(
                f"<b>Step {rec.get('step', '')}:</b> {rec.get('action', '')}",
                self.styles['Heading3']
            ))
            
            # Description
            story.append(Paragraph(rec.get('description', ''), self.styles['Normal']))
            
            # Timeline and Impact
            timeline_impact = f"<b>Timeline:</b> {rec.get('timeline', 'N/A')} | <b>Impact:</b> {rec.get('impact', 'N/A')}"
            story.append(Paragraph(timeline_impact, self.styles['Normal']))
            story.append(Spacer(1, 0.15 * inch))
        
        story.append(Spacer(1, 0.2 * inch))
        
        # Progress Tracking
        story.append(Paragraph("Track Your Progress", self.styles['CustomSubtitle']))
        
        tracking_tips = [
            "Check your credit score monthly using free services like CIBIL or Experian",
            "Maintain a checklist of action items and mark them as completed",
            "Set reminders for EMI payment dates to avoid missing payments",
            "Review your credit report every 3 months for improvements",
            "Reapply for a loan once your score reaches 700+"
        ]
        
        for tip in tracking_tips:
            story.append(Paragraph(f"✓ {tip}", self.styles['Normal']))
        
        story.append(Spacer(1, 0.3 * inch))
        
        # Expected Timeline
        story.append(Paragraph("Expected Timeline", self.styles['CustomSubtitle']))
        
        timeline_data = [
            ["Timeframe", "Expected Score Range", "Actions"],
            ["0-3 months", f"{current_score}-{current_score + 30}", "Focus on timely payments"],
            ["3-6 months", f"{current_score + 30}-{current_score + 60}", "Reduce credit utilization"],
            ["6-12 months", f"{current_score + 60}-{target_score}", "Maintain good habits"],
        ]
        
        timeline_table = Table(timeline_data, colWidths=[1.8*inch, 2*inch, 2.7*inch])
        timeline_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(timeline_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Important Notes
        story.append(Paragraph("Important Notes", self.styles['CustomSubtitle']))
        notes = [
            "Credit score improvement takes time and consistent effort",
            "There are no shortcuts - avoid companies promising instant score improvements",
            "Focus on building good financial habits for long-term success",
            "Once your score improves, you'll qualify for better loan terms and lower interest rates"
        ]
        for note in notes:
            story.append(Paragraph(f"• {note}", self.styles['Normal']))
        
        story.append(Spacer(1, 0.3 * inch))
        
        # Footer
        story.append(Paragraph(
            "<i>For personalized guidance, contact our credit counseling team at credithelp@tatacapital.com</i>",
            self.styles['Normal']
        ))
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def create_repayment_schedule(self, loan: Dict[str, Any]) -> List[Dict[str, float]]:
        """
        Create repayment schedule table for a loan.
        
        Args:
            loan: Loan details with amount, rate, tenure
        
        Returns:
            List of monthly payment breakdowns
        """
        return generate_amortization_schedule(
            loan['loan_amount'],
            loan['interest_rate'],
            loan['tenure_months'],
            loan.get('monthly_emi')
        )
