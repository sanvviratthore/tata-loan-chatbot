"""
Unit tests for Pydantic schemas and validation rules.
"""

import pytest
from pydantic import ValidationError
from schemas.models import (
    VerificationResult,
    Loan,
    CreditProfile,
    UnderwritingDecision,
    LoanOffer,
    ConsolidationOffer,
    Customer,
    SavingsBreakdown,
    PortfolioAnalysis,
    SessionState
)


class TestCustomerValidation:
    """Test Customer model validation rules."""
    
    def test_valid_customer(self):
        """Test valid customer creation."""
        customer = Customer(
            customer_id="CUST001",
            name="Rajesh Kumar",
            pan="ABCDE1234F",
            mobile="9876543210",
            email="rajesh@example.com",
            monthly_income=75000,
            employment_type="Salaried"
        )
        assert customer.customer_id == "CUST001"
        assert customer.pan == "ABCDE1234F"
        assert customer.mobile == "9876543210"
    
    def test_invalid_pan_format(self):
        """Test PAN validation with invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            Customer(
                customer_id="CUST001",
                name="Test User",
                pan="INVALID",
                mobile="9876543210",
                monthly_income=50000,
                employment_type="Salaried"
            )
        assert "Invalid PAN format" in str(exc_info.value)
    
    def test_invalid_mobile_format(self):
        """Test mobile validation with invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            Customer(
                customer_id="CUST001",
                name="Test User",
                pan="ABCDE1234F",
                mobile="123456",  # Too short
                monthly_income=50000,
                employment_type="Salaried"
            )
        assert "Invalid mobile number" in str(exc_info.value)
    
    def test_pan_case_normalization(self):
        """Test PAN is converted to uppercase."""
        customer = Customer(
            customer_id="CUST001",
            name="Test User",
            pan="abcde1234f",
            mobile="9876543210",
            monthly_income=50000,
            employment_type="Salaried"
        )
        assert customer.pan == "ABCDE1234F"


class TestCreditProfileValidation:
    """Test CreditProfile model validation rules."""
    
    def test_valid_credit_profile(self):
        """Test valid credit profile creation."""
        profile = CreditProfile(
            customer_id="CUST001",
            credit_score=720,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            monthly_income=75000
        )
        assert profile.credit_score == 720
        assert len(profile.active_loans) == 0
    
    def test_credit_score_range_validation(self):
        """Test credit score must be in valid range."""
        with pytest.raises(ValidationError):
            CreditProfile(
                customer_id="CUST001",
                credit_score=250,  # Too low
                active_loans=[],
                total_outstanding=0,
                total_monthly_emi=0
            )
        
        with pytest.raises(ValidationError):
            CreditProfile(
                customer_id="CUST001",
                credit_score=950,  # Too high
                active_loans=[],
                total_outstanding=0,
                total_monthly_emi=0
            )
    
    def test_too_many_loans_validation(self):
        """Test validation fails with too many loans."""
        loans = [
            Loan(
                loan_id=f"LOAN{i:03d}",
                loan_type="Personal",
                principal=100000,
                outstanding=50000,
                interest_rate=12.0,
                monthly_emi=5000,
                remaining_tenure=12
            )
            for i in range(11)  # 11 loans
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            CreditProfile(
                customer_id="CUST001",
                credit_score=720,
                active_loans=loans,
                total_outstanding=550000,
                total_monthly_emi=55000
            )
        assert "Too many active loans" in str(exc_info.value)


class TestLoanValidation:
    """Test Loan model validation rules."""
    
    def test_valid_loan(self):
        """Test valid loan creation."""
        loan = Loan(
            loan_id="LOAN001",
            loan_type="Personal Loan",
            lender="Bank A",
            principal=200000,
            outstanding=150000,
            interest_rate=14.5,
            monthly_emi=8500,
            remaining_tenure=18
        )
        assert loan.loan_id == "LOAN001"
        assert loan.outstanding == 150000
    
    def test_outstanding_exceeds_principal(self):
        """Test validation fails when outstanding exceeds principal."""
        with pytest.raises(ValidationError) as exc_info:
            Loan(
                loan_id="LOAN001",
                loan_type="Personal",
                principal=100000,
                outstanding=150000,  # More than principal
                interest_rate=12.0,
                monthly_emi=5000,
                remaining_tenure=12
            )
        assert "Outstanding amount cannot exceed principal" in str(exc_info.value)


class TestUnderwritingDecisionValidation:
    """Test UnderwritingDecision model validation."""
    
    def test_approved_decision(self):
        """Test approved underwriting decision."""
        decision = UnderwritingDecision(
            approved=True,
            loan_amount=300000,
            interest_rate=10.5,
            tenure_months=60,
            monthly_emi=6420,
            credit_score_tier="Excellent",
            max_eligible_amount=500000
        )
        assert decision.approved is True
        assert decision.loan_amount == 300000
    
    def test_rejected_decision(self):
        """Test rejected underwriting decision."""
        decision = UnderwritingDecision(
            approved=False,
            rejection_reason="Credit score too low",
            improvement_plan=["Pay bills on time", "Reduce credit utilization"]
        )
        assert decision.approved is False
        assert decision.rejection_reason is not None


class TestConsolidationOfferValidation:
    """Test ConsolidationOffer model validation."""
    
    def test_valid_consolidation_offer(self):
        """Test valid consolidation offer."""
        loans = [
            Loan(
                loan_id="LOAN001",
                loan_type="Personal",
                principal=100000,
                outstanding=80000,
                interest_rate=14.0,
                monthly_emi=5000,
                remaining_tenure=18
            ),
            Loan(
                loan_id="LOAN002",
                loan_type="Credit Card",
                principal=50000,
                outstanding=40000,
                interest_rate=18.0,
                monthly_emi=4000,
                remaining_tenure=12
            )
        ]
        
        offer = ConsolidationOffer(
            offer_id="CONSOL001",
            customer_id="CUST001",
            consolidated_amount=120000,
            new_interest_rate=12.0,
            new_tenure_months=24,
            new_monthly_emi=5650,
            current_total_emi=9000,
            monthly_savings=3350,
            total_interest_savings=30000,
            loans_being_consolidated=loans,
            comparison_table={}
        )
        assert offer.monthly_savings == 3350
        assert len(offer.loans_being_consolidated) == 2
    
    def test_insufficient_loans_for_consolidation(self):
        """Test validation fails with less than 2 loans."""
        loan = Loan(
            loan_id="LOAN001",
            loan_type="Personal",
            principal=100000,
            outstanding=80000,
            interest_rate=14.0,
            monthly_emi=5000,
            remaining_tenure=18
        )
        
        with pytest.raises(ValidationError) as exc_info:
            ConsolidationOffer(
                offer_id="CONSOL001",
                customer_id="CUST001",
                consolidated_amount=80000,
                new_interest_rate=12.0,
                new_tenure_months=24,
                new_monthly_emi=3800,
                current_total_emi=5000,
                monthly_savings=1200,
                total_interest_savings=15000,
                loans_being_consolidated=[loan],  # Only 1 loan
                comparison_table={}
            )
        assert "at least 2 items" in str(exc_info.value) or "Consolidation requires at least 2 loans" in str(exc_info.value)


class TestVerificationResultValidation:
    """Test VerificationResult model validation."""
    
    def test_successful_verification(self):
        """Test successful verification result."""
        result = VerificationResult(
            success=True,
            customer_id="CUST001",
            name="Rajesh Kumar",
            retry_count=0
        )
        assert result.success is True
        assert result.customer_id == "CUST001"
    
    def test_failed_verification(self):
        """Test failed verification result."""
        result = VerificationResult(
            success=False,
            error_message="Customer not found",
            retry_count=1
        )
        assert result.success is False
        assert result.error_message is not None
    
    def test_retry_count_limits(self):
        """Test retry count validation."""
        with pytest.raises(ValidationError):
            VerificationResult(
                success=False,
                error_message="Failed",
                retry_count=5  # Exceeds max of 3
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
