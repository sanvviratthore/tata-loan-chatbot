"""
Unit tests for Document Agent
"""

import pytest
from io import BytesIO
from datetime import datetime
from PyPDF2 import PdfReader

from agents.document_agent import DocumentAgent
from agents.base_agent import ValidationError


@pytest.fixture
def document_agent():
    """Create document agent instance."""
    return DocumentAgent()


@pytest.fixture
def sample_customer():
    """Sample customer data."""
    return {
        "customer_id": "CUST001",
        "name": "Rajesh Kumar",
        "pan": "ABCDE1234F",
        "mobile": "9876543210",
        "email": "rajesh.kumar@example.com",
        "monthly_income": 75000,
        "employment_type": "Salaried"
    }


@pytest.fixture
def sample_loan_offer():
    """Sample loan offer data."""
    return {
        "offer_id": "OFFER001",
        "customer_id": "CUST001",
        "loan_amount": 300000,
        "interest_rate": 10.5,
        "tenure_months": 60,
        "monthly_emi": 6420,
        "processing_fee": 3000,
        "total_interest": 85200,
        "total_repayment": 385200,
        "offer_valid_until": "2025-01-15",
        "special_conditions": ["Pre-payment allowed after 6 months"]
    }


@pytest.fixture
def sample_consolidation_offer():
    """Sample consolidation offer data."""
    return {
        "offer_id": "CONSOL001",
        "customer_id": "CUST001",
        "consolidated_amount": 200000,
        "new_interest_rate": 12.5,
        "new_tenure_months": 24,
        "new_monthly_emi": 9500,
        "current_total_emi": 13500,
        "monthly_savings": 4000,
        "total_interest_savings": 50000,
        "loans_being_consolidated": [
            {
                "loan_id": "LOAN001",
                "loan_type": "Personal Loan",
                "lender": "Bank A",
                "principal": 200000,
                "outstanding": 150000,
                "interest_rate": 14.5,
                "monthly_emi": 8500,
                "remaining_tenure": 18
            },
            {
                "loan_id": "LOAN002",
                "loan_type": "Credit Card",
                "lender": "Bank B",
                "principal": 50000,
                "outstanding": 50000,
                "interest_rate": 18.0,
                "monthly_emi": 5000,
                "remaining_tenure": 12
            }
        ],
        "comparison_table": {}
    }


@pytest.fixture
def sample_improvement_plan():
    """Sample credit improvement plan data."""
    return {
        "current_credit_score": 620,
        "target_credit_score": 750,
        "timeline": "6-12 months",
        "issues": [
            "Multiple late payments in the last 6 months",
            "High credit utilization (85%)",
            "Too many recent credit inquiries"
        ],
        "recommendations": [
            {
                "step": 1,
                "action": "Pay all EMIs on time",
                "description": "Set up auto-debit for all loan EMIs to ensure timely payments.",
                "timeline": "Immediate - Ongoing",
                "impact": "High"
            },
            {
                "step": 2,
                "action": "Reduce credit utilization",
                "description": "Keep credit card utilization below 30% of the limit.",
                "timeline": "1-3 months",
                "impact": "High"
            }
        ]
    }


class TestDocumentAgentValidation:
    """Test input validation."""
    
    def test_validate_input_missing_document_type(self, document_agent):
        """Test validation fails when document_type is missing."""
        with pytest.raises(ValidationError) as exc_info:
            document_agent.validate_input({})
        assert "document_type is required" in str(exc_info.value)
    
    def test_validate_input_invalid_document_type(self, document_agent):
        """Test validation fails for invalid document type."""
        with pytest.raises(ValidationError) as exc_info:
            document_agent.validate_input({"document_type": "invalid_type"})
        assert "Invalid document_type" in str(exc_info.value)
    
    def test_validate_input_loan_offer_missing_data(self, document_agent):
        """Test validation fails when loan offer data is missing."""
        with pytest.raises(ValidationError) as exc_info:
            document_agent.validate_input({"document_type": "loan_offer"})
        assert "offer and customer data required" in str(exc_info.value)
    
    def test_validate_input_consolidation_missing_data(self, document_agent):
        """Test validation fails when consolidation data is missing."""
        with pytest.raises(ValidationError) as exc_info:
            document_agent.validate_input({"document_type": "consolidation_report"})
        assert "consolidation_offer and customer data required" in str(exc_info.value)
    
    def test_validate_input_improvement_plan_missing_data(self, document_agent):
        """Test validation fails when improvement plan data is missing."""
        with pytest.raises(ValidationError) as exc_info:
            document_agent.validate_input({"document_type": "credit_improvement_plan"})
        assert "improvement_plan and customer data required" in str(exc_info.value)
    
    def test_validate_input_valid_loan_offer(self, document_agent, sample_loan_offer, sample_customer):
        """Test validation passes for valid loan offer input."""
        input_data = {
            "document_type": "loan_offer",
            "offer": sample_loan_offer,
            "customer": sample_customer
        }
        assert document_agent.validate_input(input_data) is True


class TestLoanOfferGeneration:
    """Test loan offer letter generation."""
    
    def test_generate_offer_letter_returns_bytes(self, document_agent, sample_loan_offer, sample_customer):
        """Test that offer letter generation returns PDF bytes."""
        pdf_bytes = document_agent.generate_offer_letter(sample_loan_offer, sample_customer)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
    
    def test_generate_offer_letter_valid_pdf(self, document_agent, sample_loan_offer, sample_customer):
        """Test that generated offer letter is a valid PDF."""
        pdf_bytes = document_agent.generate_offer_letter(sample_loan_offer, sample_customer)
        
        # Try to read the PDF
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        assert len(pdf_reader.pages) > 0
    
    def test_generate_offer_letter_contains_customer_info(self, document_agent, sample_loan_offer, sample_customer):
        """Test that offer letter contains customer information."""
        pdf_bytes = document_agent.generate_offer_letter(sample_loan_offer, sample_customer)
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        assert sample_customer["name"] in text
        assert sample_customer["customer_id"] in text
        assert sample_customer["pan"] in text
    
    def test_generate_offer_letter_contains_loan_details(self, document_agent, sample_loan_offer, sample_customer):
        """Test that offer letter contains loan details."""
        pdf_bytes = document_agent.generate_offer_letter(sample_loan_offer, sample_customer)
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        assert sample_loan_offer["offer_id"] in text
        # Check for loan amount with comma formatting
        assert "300,000" in text or str(sample_loan_offer["loan_amount"]) in text
        assert str(sample_loan_offer["interest_rate"]) in text
        assert str(sample_loan_offer["tenure_months"]) in text
    
    def test_generate_offer_letter_contains_repayment_schedule(self, document_agent, sample_loan_offer, sample_customer):
        """Test that offer letter contains repayment schedule."""
        pdf_bytes = document_agent.generate_offer_letter(sample_loan_offer, sample_customer)
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        assert "Repayment Schedule" in text
        assert "Month" in text
        assert "EMI" in text
        assert "Interest" in text
        assert "Principal" in text
    
    def test_generate_offer_letter_with_special_conditions(self, document_agent, sample_loan_offer, sample_customer):
        """Test that special conditions are included in offer letter."""
        pdf_bytes = document_agent.generate_offer_letter(sample_loan_offer, sample_customer)
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        assert "Special Conditions" in text
        assert sample_loan_offer["special_conditions"][0] in text


class TestConsolidationReportGeneration:
    """Test consolidation report generation."""
    
    def test_generate_consolidation_report_returns_bytes(self, document_agent, 
                                                         sample_consolidation_offer, sample_customer):
        """Test that consolidation report generation returns PDF bytes."""
        pdf_bytes = document_agent.generate_consolidation_report(
            sample_consolidation_offer, sample_customer
        )
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
    
    def test_generate_consolidation_report_valid_pdf(self, document_agent, 
                                                     sample_consolidation_offer, sample_customer):
        """Test that generated consolidation report is a valid PDF."""
        pdf_bytes = document_agent.generate_consolidation_report(
            sample_consolidation_offer, sample_customer
        )
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        assert len(pdf_reader.pages) > 0
    
    def test_generate_consolidation_report_contains_savings(self, document_agent, 
                                                           sample_consolidation_offer, sample_customer):
        """Test that consolidation report highlights savings."""
        pdf_bytes = document_agent.generate_consolidation_report(
            sample_consolidation_offer, sample_customer
        )
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        assert "Savings" in text
        # Check for savings with comma formatting
        assert "4,000" in text or str(sample_consolidation_offer["monthly_savings"]) in text
        assert "50,000" in text or str(sample_consolidation_offer["total_interest_savings"]) in text
    
    def test_generate_consolidation_report_contains_current_loans(self, document_agent, 
                                                                  sample_consolidation_offer, sample_customer):
        """Test that consolidation report lists current loans."""
        pdf_bytes = document_agent.generate_consolidation_report(
            sample_consolidation_offer, sample_customer
        )
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        assert "Current Loans" in text
        for loan in sample_consolidation_offer["loans_being_consolidated"]:
            assert loan["loan_type"] in text
    
    def test_generate_consolidation_report_contains_comparison(self, document_agent, 
                                                               sample_consolidation_offer, sample_customer):
        """Test that consolidation report contains comparison table."""
        pdf_bytes = document_agent.generate_consolidation_report(
            sample_consolidation_offer, sample_customer
        )
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        assert "Comparison" in text
        assert "Current" in text or "Consolidated" in text
    
    def test_generate_consolidation_report_contains_benefits(self, document_agent, 
                                                            sample_consolidation_offer, sample_customer):
        """Test that consolidation report lists benefits."""
        pdf_bytes = document_agent.generate_consolidation_report(
            sample_consolidation_offer, sample_customer
        )
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        assert "Benefits" in text


class TestCreditImprovementPlanGeneration:
    """Test credit improvement plan generation."""
    
    def test_generate_improvement_plan_returns_bytes(self, document_agent, 
                                                     sample_improvement_plan, sample_customer):
        """Test that improvement plan generation returns PDF bytes."""
        pdf_bytes = document_agent.generate_credit_improvement_plan(
            sample_improvement_plan, sample_customer
        )
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
    
    def test_generate_improvement_plan_valid_pdf(self, document_agent, 
                                                sample_improvement_plan, sample_customer):
        """Test that generated improvement plan is a valid PDF."""
        pdf_bytes = document_agent.generate_credit_improvement_plan(
            sample_improvement_plan, sample_customer
        )
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        assert len(pdf_reader.pages) > 0
    
    def test_generate_improvement_plan_contains_scores(self, document_agent, 
                                                      sample_improvement_plan, sample_customer):
        """Test that improvement plan contains credit scores."""
        pdf_bytes = document_agent.generate_credit_improvement_plan(
            sample_improvement_plan, sample_customer
        )
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        assert str(sample_improvement_plan["current_credit_score"]) in text
        assert str(sample_improvement_plan["target_credit_score"]) in text
    
    def test_generate_improvement_plan_contains_issues(self, document_agent, 
                                                      sample_improvement_plan, sample_customer):
        """Test that improvement plan lists identified issues."""
        pdf_bytes = document_agent.generate_credit_improvement_plan(
            sample_improvement_plan, sample_customer
        )
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        assert "Issues" in text
        for issue in sample_improvement_plan["issues"]:
            # Check if key words from issues are present
            assert any(word in text for word in issue.split()[:3])
    
    def test_generate_improvement_plan_contains_recommendations(self, document_agent, 
                                                               sample_improvement_plan, sample_customer):
        """Test that improvement plan contains actionable recommendations."""
        pdf_bytes = document_agent.generate_credit_improvement_plan(
            sample_improvement_plan, sample_customer
        )
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        assert "Action Plan" in text
        for rec in sample_improvement_plan["recommendations"]:
            assert rec["action"] in text
    
    def test_generate_improvement_plan_contains_timeline(self, document_agent, 
                                                        sample_improvement_plan, sample_customer):
        """Test that improvement plan contains expected timeline."""
        pdf_bytes = document_agent.generate_credit_improvement_plan(
            sample_improvement_plan, sample_customer
        )
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        assert "Timeline" in text
        assert sample_improvement_plan["timeline"] in text
    
    def test_generate_improvement_plan_with_default_recommendations(self, document_agent, sample_customer):
        """Test that improvement plan generates default recommendations when none provided."""
        minimal_plan = {
            "current_credit_score": 620,
            "target_credit_score": 750,
            "timeline": "6-12 months"
        }
        
        pdf_bytes = document_agent.generate_credit_improvement_plan(minimal_plan, sample_customer)
        
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        # Should contain default recommendations
        assert "Pay all EMIs on time" in text
        assert "credit utilization" in text


class TestDocumentAgentProcess:
    """Test main process method."""
    
    def test_process_loan_offer_success(self, document_agent, sample_loan_offer, sample_customer):
        """Test successful loan offer document generation through process method."""
        input_data = {
            "document_type": "loan_offer",
            "offer": sample_loan_offer,
            "customer": sample_customer
        }
        session_state = {}
        
        result = document_agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert "pdf_bytes" in result["data"]
        assert "filename" in result["data"]
        assert result["data"]["filename"].startswith("loan_offer_")
        assert result["data"]["filename"].endswith(".pdf")
    
    def test_process_consolidation_report_success(self, document_agent, 
                                                  sample_consolidation_offer, sample_customer):
        """Test successful consolidation report generation through process method."""
        input_data = {
            "document_type": "consolidation_report",
            "consolidation_offer": sample_consolidation_offer,
            "customer": sample_customer
        }
        session_state = {}
        
        result = document_agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert "pdf_bytes" in result["data"]
        assert "filename" in result["data"]
        assert result["data"]["filename"].startswith("consolidation_report_")
    
    def test_process_improvement_plan_success(self, document_agent, 
                                             sample_improvement_plan, sample_customer):
        """Test successful improvement plan generation through process method."""
        input_data = {
            "document_type": "credit_improvement_plan",
            "improvement_plan": sample_improvement_plan,
            "customer": sample_customer
        }
        session_state = {}
        
        result = document_agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert "pdf_bytes" in result["data"]
        assert "filename" in result["data"]
        assert result["data"]["filename"].startswith("credit_improvement_plan_")
    
    def test_process_invalid_document_type(self, document_agent):
        """Test process method with invalid document type."""
        input_data = {
            "document_type": "invalid_type"
        }
        session_state = {}
        
        with pytest.raises(ValidationError):
            document_agent.process(input_data, session_state)


class TestRepaymentSchedule:
    """Test repayment schedule creation."""
    
    def test_create_repayment_schedule(self, document_agent):
        """Test repayment schedule creation."""
        loan = {
            "loan_amount": 100000,
            "interest_rate": 12.0,
            "tenure_months": 12,
            "monthly_emi": 8885
        }
        
        schedule = document_agent.create_repayment_schedule(loan)
        
        assert len(schedule) == 12
        assert all("month" in entry for entry in schedule)
        assert all("emi" in entry for entry in schedule)
        assert all("interest" in entry for entry in schedule)
        assert all("principal" in entry for entry in schedule)
        assert schedule[0]["month"] == 1
        assert schedule[-1]["month"] == 12
        assert schedule[-1]["closing_balance"] == 0
