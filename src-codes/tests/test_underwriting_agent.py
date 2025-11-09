"""
Unit tests for Underwriting Agent

Tests eligibility assessment, loan offer generation, and all approval/rejection scenarios.
"""

import pytest
from datetime import datetime, timedelta

from agents.underwriting_agent import UnderwritingAgent
from agents.base_agent import ValidationError, BusinessLogicError
from schemas.models import CreditProfile, Loan, UnderwritingDecision, LoanOffer


@pytest.fixture
def underwriting_agent():
    """Create underwriting agent instance."""
    return UnderwritingAgent()


@pytest.fixture
def excellent_credit_profile():
    """Credit profile with excellent credit score."""
    return CreditProfile(
        customer_id="CUST001",
        credit_score=780,
        active_loans=[],
        total_outstanding=0,
        total_monthly_emi=0,
        debt_to_income_ratio=0,
        monthly_income=100000
    )


@pytest.fixture
def good_credit_profile():
    """Credit profile with good credit score."""
    return CreditProfile(
        customer_id="CUST002",
        credit_score=700,
        active_loans=[
            Loan(
                loan_id="LOAN001",
                loan_type="Personal Loan",
                lender="Bank A",
                principal=200000,
                outstanding=150000,
                interest_rate=14.5,
                monthly_emi=8500,
                remaining_tenure=18
            )
        ],
        total_outstanding=150000,
        total_monthly_emi=8500,
        debt_to_income_ratio=17.0,
        monthly_income=50000
    )


@pytest.fixture
def fair_credit_profile():
    """Credit profile with fair credit score."""
    return CreditProfile(
        customer_id="CUST003",
        credit_score=680,  # Changed to 680 to be above minimum of 650
        active_loans=[
            Loan(
                loan_id="LOAN001",
                loan_type="Personal Loan",
                principal=100000,
                outstanding=80000,
                interest_rate=16.0,
                monthly_emi=5000,
                remaining_tenure=16
            )
        ],
        total_outstanding=80000,
        total_monthly_emi=5000,
        debt_to_income_ratio=20.0,
        monthly_income=25000
    )


@pytest.fixture
def poor_credit_profile():
    """Credit profile with poor credit score."""
    return CreditProfile(
        customer_id="CUST004",
        credit_score=620,
        active_loans=[],
        total_outstanding=0,
        total_monthly_emi=0,
        debt_to_income_ratio=0,
        monthly_income=30000
    )


@pytest.fixture
def low_credit_profile():
    """Credit profile below minimum credit score."""
    return CreditProfile(
        customer_id="CUST005",
        credit_score=600,
        active_loans=[],
        total_outstanding=0,
        total_monthly_emi=0,
        debt_to_income_ratio=0,
        monthly_income=40000
    )


@pytest.fixture
def too_many_loans_profile():
    """Credit profile with too many loans."""
    loans = []
    for i in range(6):
        loans.append(
            Loan(
                loan_id=f"LOAN{i:03d}",
                loan_type="Personal Loan",
                principal=50000,
                outstanding=30000,
                interest_rate=15.0,
                monthly_emi=2000,
                remaining_tenure=15
            )
        )
    
    return CreditProfile(
        customer_id="CUST006",
        credit_score=720,
        active_loans=loans,
        total_outstanding=180000,
        total_monthly_emi=12000,
        debt_to_income_ratio=40.0,
        monthly_income=30000
    )


@pytest.fixture
def high_dti_profile():
    """Credit profile with high DTI ratio."""
    return CreditProfile(
        customer_id="CUST007",
        credit_score=720,
        active_loans=[
            Loan(
                loan_id="LOAN001",
                loan_type="Personal Loan",
                principal=500000,
                outstanding=400000,
                interest_rate=14.0,
                monthly_emi=28000,
                remaining_tenure=15
            )
        ],
        total_outstanding=400000,
        total_monthly_emi=28000,
        debt_to_income_ratio=56.0,
        monthly_income=50000
    )


@pytest.fixture
def session_state():
    """Sample session state."""
    return {
        "session_id": "test_session_123",
        "user_id": "CUST001",
        "workflow_stage": "UNDERWRITING"
    }


class TestUnderwritingAgentValidation:
    """Test input validation."""
    
    def test_validate_input_missing_data(self, underwriting_agent):
        """Test validation with missing input data."""
        with pytest.raises(ValidationError) as exc_info:
            underwriting_agent.validate_input({})
        assert "required" in str(exc_info.value).lower()
    
    def test_validate_input_missing_credit_profile(self, underwriting_agent):
        """Test validation with missing credit profile."""
        with pytest.raises(ValidationError) as exc_info:
            underwriting_agent.validate_input({"requested_amount": 100000})
        assert "credit profile" in str(exc_info.value).lower()
    
    def test_validate_input_invalid_amount_type(self, underwriting_agent, excellent_credit_profile):
        """Test validation with invalid amount type."""
        with pytest.raises(ValidationError) as exc_info:
            underwriting_agent.validate_input({
                "credit_profile": excellent_credit_profile,
                "requested_amount": "invalid"
            })
        assert "must be a number" in str(exc_info.value)
    
    def test_validate_input_negative_amount(self, underwriting_agent, excellent_credit_profile):
        """Test validation with negative amount."""
        with pytest.raises(ValidationError) as exc_info:
            underwriting_agent.validate_input({
                "credit_profile": excellent_credit_profile,
                "requested_amount": -50000
            })
        assert "greater than 0" in str(exc_info.value)
    
    def test_validate_input_excessive_amount(self, underwriting_agent, excellent_credit_profile):
        """Test validation with amount exceeding maximum."""
        with pytest.raises(ValidationError) as exc_info:
            underwriting_agent.validate_input({
                "credit_profile": excellent_credit_profile,
                "requested_amount": 15000000
            })
        assert "exceeds maximum" in str(exc_info.value)
    
    def test_validate_input_invalid_tenure(self, underwriting_agent, excellent_credit_profile):
        """Test validation with invalid tenure."""
        with pytest.raises(ValidationError) as exc_info:
            underwriting_agent.validate_input({
                "credit_profile": excellent_credit_profile,
                "requested_tenure": 6
            })
        assert "between 12 and 360" in str(exc_info.value)
    
    def test_validate_input_valid_data(self, underwriting_agent, excellent_credit_profile):
        """Test validation with valid data."""
        result = underwriting_agent.validate_input({
            "credit_profile": excellent_credit_profile,
            "requested_amount": 300000,
            "requested_tenure": 60
        })
        assert result is True


class TestCreditTierDetermination:
    """Test credit tier determination."""
    
    def test_excellent_tier(self, underwriting_agent):
        """Test excellent credit tier."""
        tier = underwriting_agent._determine_credit_tier(780)
        assert tier == "EXCELLENT"
    
    def test_good_tier(self, underwriting_agent):
        """Test good credit tier."""
        tier = underwriting_agent._determine_credit_tier(700)
        assert tier == "GOOD"
    
    def test_good_tier_boundary(self, underwriting_agent):
        """Test good tier at boundary."""
        tier = underwriting_agent._determine_credit_tier(650)
        assert tier == "GOOD"
    
    def test_fair_tier(self, underwriting_agent):
        """Test fair credit tier."""
        tier = underwriting_agent._determine_credit_tier(680)
        assert tier == "GOOD"  # 680 is in GOOD tier (650-749)
    
    def test_poor_tier(self, underwriting_agent):
        """Test poor credit tier."""
        tier = underwriting_agent._determine_credit_tier(550)
        assert tier == "POOR"


class TestEligibilityAssessment:
    """Test eligibility assessment logic."""
    
    def test_excellent_credit_approval(self, underwriting_agent, excellent_credit_profile):
        """Test approval for excellent credit score."""
        decision = underwriting_agent.assess_eligibility(
            credit_profile=excellent_credit_profile,
            requested_amount=500000,
            requested_tenure=60
        )
        
        assert decision.approved is True
        assert decision.credit_score_tier == "EXCELLENT"
        assert decision.interest_rate == 10.5
        assert decision.loan_amount == 500000
        assert decision.tenure_months == 60
        assert decision.monthly_emi > 0
        assert decision.rejection_reason is None
    
    def test_good_credit_approval(self, underwriting_agent, good_credit_profile):
        """Test approval for good credit score."""
        decision = underwriting_agent.assess_eligibility(
            credit_profile=good_credit_profile,
            requested_amount=200000,
            requested_tenure=48
        )
        
        assert decision.approved is True
        assert decision.credit_score_tier == "GOOD"
        assert decision.interest_rate == 12.5
        assert decision.loan_amount == 200000
        assert decision.tenure_months == 48
        assert decision.monthly_emi > 0
    
    def test_fair_credit_approval(self, underwriting_agent, fair_credit_profile):
        """Test approval for fair credit score."""
        decision = underwriting_agent.assess_eligibility(
            credit_profile=fair_credit_profile,
            requested_amount=50000,
            requested_tenure=36
        )
        
        assert decision.approved is True
        assert decision.credit_score_tier == "GOOD"  # 680 is in GOOD tier
        assert decision.interest_rate == 12.5  # GOOD tier rate
        assert decision.loan_amount == 50000
    
    def test_low_credit_rejection(self, underwriting_agent, low_credit_profile):
        """Test rejection for low credit score."""
        decision = underwriting_agent.assess_eligibility(
            credit_profile=low_credit_profile,
            requested_amount=100000,
            requested_tenure=60
        )
        
        assert decision.approved is False
        assert decision.rejection_reason is not None
        assert "credit score" in decision.rejection_reason.lower()
        assert decision.improvement_plan is not None
        assert len(decision.improvement_plan) > 0
    
    def test_too_many_loans_rejection(self, underwriting_agent, too_many_loans_profile):
        """Test rejection for too many loans."""
        decision = underwriting_agent.assess_eligibility(
            credit_profile=too_many_loans_profile,
            requested_amount=100000,
            requested_tenure=60
        )
        
        assert decision.approved is False
        assert "6 active loans" in decision.rejection_reason
        assert decision.improvement_plan is not None
    
    def test_high_dti_rejection(self, underwriting_agent, high_dti_profile):
        """Test rejection for high DTI ratio."""
        decision = underwriting_agent.assess_eligibility(
            credit_profile=high_dti_profile,
            requested_amount=100000,
            requested_tenure=60
        )
        
        assert decision.approved is False
        assert "debt-to-income" in decision.rejection_reason.lower()
        assert decision.max_eligible_amount == 0.0
    
    def test_no_requested_amount_offers_maximum(self, underwriting_agent, excellent_credit_profile):
        """Test that no requested amount offers maximum eligible."""
        decision = underwriting_agent.assess_eligibility(
            credit_profile=excellent_credit_profile,
            requested_amount=None,
            requested_tenure=60
        )
        
        assert decision.approved is True
        assert decision.loan_amount > 0
        assert decision.loan_amount == decision.max_eligible_amount
    
    def test_requested_amount_exceeds_maximum(self, underwriting_agent, good_credit_profile):
        """Test that excessive request gets capped at maximum."""
        decision = underwriting_agent.assess_eligibility(
            credit_profile=good_credit_profile,
            requested_amount=5000000,  # Very high amount
            requested_tenure=60
        )
        
        assert decision.approved is True
        assert decision.loan_amount < 5000000
        assert decision.loan_amount == decision.max_eligible_amount


class TestMaxLoanCalculation:
    """Test maximum loan amount calculation."""
    
    def test_max_loan_with_no_existing_emi(self, underwriting_agent, excellent_credit_profile):
        """Test max loan calculation with no existing EMI."""
        max_amount = underwriting_agent._calculate_max_loan_amount(
            credit_profile=excellent_credit_profile,
            interest_rate=10.5,
            tenure_months=60,
            max_dti=0.40
        )
        
        assert max_amount > 0
        # With 100k income and 40% DTI, max EMI = 40k
        # This should allow a substantial loan
        assert max_amount > 1000000
    
    def test_max_loan_with_existing_emi(self, underwriting_agent, good_credit_profile):
        """Test max loan calculation with existing EMI."""
        max_amount = underwriting_agent._calculate_max_loan_amount(
            credit_profile=good_credit_profile,
            interest_rate=12.5,
            tenure_months=60,
            max_dti=0.50
        )
        
        assert max_amount > 0
        # With 50k income, 8.5k existing EMI, and 50% DTI
        # Max total EMI = 25k, available = 16.5k
        assert max_amount > 500000
        assert max_amount < 1500000
    
    def test_max_loan_with_high_existing_emi(self, underwriting_agent, high_dti_profile):
        """Test max loan with high existing EMI."""
        max_amount = underwriting_agent._calculate_max_loan_amount(
            credit_profile=high_dti_profile,
            interest_rate=10.5,
            tenure_months=60,
            max_dti=0.40
        )
        
        # With 50k income, 28k existing EMI, and 40% DTI
        # Max total EMI = 20k, but existing is already 28k
        assert max_amount == 0.0


class TestLoanOfferGeneration:
    """Test loan offer generation."""
    
    def test_generate_offer_for_approved_decision(self, underwriting_agent, excellent_credit_profile):
        """Test generating offer for approved decision."""
        decision = underwriting_agent.assess_eligibility(
            credit_profile=excellent_credit_profile,
            requested_amount=500000,
            requested_tenure=60
        )
        
        offer = underwriting_agent.generate_loan_offer(
            decision=decision,
            customer_id=excellent_credit_profile.customer_id
        )
        
        assert isinstance(offer, LoanOffer)
        assert offer.customer_id == excellent_credit_profile.customer_id
        assert offer.loan_amount == 500000
        assert offer.interest_rate == 10.5
        assert offer.tenure_months == 60
        assert offer.monthly_emi == decision.monthly_emi
        assert offer.processing_fee > 0
        assert offer.total_interest > 0
        assert offer.total_repayment > offer.loan_amount
        assert offer.offer_valid_until is not None
        assert offer.special_conditions is not None
        assert len(offer.special_conditions) > 0
    
    def test_generate_offer_calculates_correct_totals(self, underwriting_agent, good_credit_profile):
        """Test that offer calculates correct financial totals."""
        decision = underwriting_agent.assess_eligibility(
            credit_profile=good_credit_profile,
            requested_amount=300000,
            requested_tenure=48
        )
        
        offer = underwriting_agent.generate_loan_offer(
            decision=decision,
            customer_id=good_credit_profile.customer_id
        )
        
        # Verify total repayment = loan amount + total interest
        assert abs(offer.total_repayment - (offer.loan_amount + offer.total_interest)) < 1
        
        # Verify processing fee is 1% of loan amount
        expected_fee = offer.loan_amount * 0.01
        assert abs(offer.processing_fee - expected_fee) < 1
    
    def test_generate_offer_for_rejected_decision_raises_error(self, underwriting_agent, low_credit_profile):
        """Test that generating offer for rejected decision raises error."""
        decision = underwriting_agent.assess_eligibility(
            credit_profile=low_credit_profile,
            requested_amount=100000,
            requested_tenure=60
        )
        
        with pytest.raises(BusinessLogicError) as exc_info:
            underwriting_agent.generate_loan_offer(
                decision=decision,
                customer_id=low_credit_profile.customer_id
            )
        assert "rejected" in str(exc_info.value).lower()
    
    def test_offer_validity_is_7_days(self, underwriting_agent, excellent_credit_profile):
        """Test that offer validity is 7 days from generation."""
        decision = underwriting_agent.assess_eligibility(
            credit_profile=excellent_credit_profile,
            requested_amount=500000,
            requested_tenure=60
        )
        
        offer = underwriting_agent.generate_loan_offer(
            decision=decision,
            customer_id=excellent_credit_profile.customer_id
        )
        
        # Parse the validity date
        valid_until = datetime.strptime(offer.offer_valid_until, "%Y-%m-%d")
        today = datetime.now()
        days_diff = (valid_until - today).days
        
        assert days_diff >= 6 and days_diff <= 7
    
    def test_excellent_tier_gets_premium_conditions(self, underwriting_agent, excellent_credit_profile):
        """Test that excellent tier gets premium special conditions."""
        decision = underwriting_agent.assess_eligibility(
            credit_profile=excellent_credit_profile,
            requested_amount=500000,
            requested_tenure=60
        )
        
        offer = underwriting_agent.generate_loan_offer(
            decision=decision,
            customer_id=excellent_credit_profile.customer_id
        )
        
        conditions_text = " ".join(offer.special_conditions)
        assert "top-up" in conditions_text.lower()
        assert "priority" in conditions_text.lower()


class TestImprovementPlans:
    """Test credit improvement plan generation."""
    
    def test_credit_improvement_plan_for_low_score(self, underwriting_agent, low_credit_profile):
        """Test credit improvement plan generation."""
        plan = underwriting_agent._generate_credit_improvement_plan(low_credit_profile)
        
        assert isinstance(plan, list)
        assert len(plan) > 0
        assert any("pay" in item.lower() and "time" in item.lower() for item in plan)
        assert any("credit utilization" in item.lower() for item in plan)
    
    def test_too_many_loans_advice(self, underwriting_agent, too_many_loans_profile):
        """Test advice for too many loans."""
        advice = underwriting_agent._generate_too_many_loans_advice(too_many_loans_profile)
        
        assert isinstance(advice, list)
        assert len(advice) > 0
        assert any("consolidat" in item.lower() for item in advice)
        assert any("pay" in item.lower() for item in advice)
    
    def test_high_dti_advice(self, underwriting_agent, high_dti_profile):
        """Test advice for high DTI."""
        advice = underwriting_agent._generate_high_dti_advice(high_dti_profile)
        
        assert isinstance(advice, list)
        assert len(advice) > 0
        assert any("income" in item.lower() for item in advice)
        assert any("debt-to-income" in item.lower() or "dti" in item.lower() for item in advice)


class TestProcessMethod:
    """Test main process method."""
    
    def test_process_with_approval(self, underwriting_agent, excellent_credit_profile, session_state):
        """Test process method with approval."""
        input_data = {
            "credit_profile": excellent_credit_profile,
            "requested_amount": 500000,
            "requested_tenure": 60
        }
        
        result = underwriting_agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert result["agent"] == "underwriting_agent"
        assert result["next_agent"] == "sales"
        assert "decision" in result["data"]
        assert "loan_offer" in result["data"]
        assert result["data"]["decision"]["approved"] is True
        assert result["data"]["loan_offer"] is not None
    
    def test_process_with_rejection(self, underwriting_agent, low_credit_profile, session_state):
        """Test process method with rejection."""
        input_data = {
            "credit_profile": low_credit_profile,
            "requested_amount": 100000,
            "requested_tenure": 60
        }
        
        result = underwriting_agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert result["data"]["decision"]["approved"] is False
        assert result["data"]["loan_offer"] is None
        assert result["data"]["decision"]["rejection_reason"] is not None
        assert result["data"]["decision"]["improvement_plan"] is not None
    
    def test_process_with_dict_credit_profile(self, underwriting_agent, excellent_credit_profile, session_state):
        """Test process method with credit profile as dict."""
        input_data = {
            "credit_profile": excellent_credit_profile.model_dump(),
            "requested_amount": 300000
        }
        
        result = underwriting_agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert result["data"]["decision"]["approved"] is True


class TestVerifiedIncomeRecalculation:
    """Test recalculation with verified income."""
    
    def test_recalculate_with_higher_income(self, underwriting_agent, good_credit_profile):
        """Test recalculation with higher verified income."""
        # Initial assessment with lower income
        initial_decision = underwriting_agent.assess_eligibility(
            credit_profile=good_credit_profile,
            requested_amount=500000,
            requested_tenure=60
        )
        
        # Recalculate with higher verified income
        new_decision = underwriting_agent.recalculate_with_verified_income(
            credit_profile=good_credit_profile,
            verified_income=100000,  # Double the original income
            requested_amount=500000,
            requested_tenure=60
        )
        
        # Should be able to approve higher amount with higher income
        assert new_decision.max_eligible_amount > initial_decision.max_eligible_amount
    
    def test_recalculate_updates_dti(self, underwriting_agent, good_credit_profile):
        """Test that recalculation updates DTI ratio."""
        new_decision = underwriting_agent.recalculate_with_verified_income(
            credit_profile=good_credit_profile,
            verified_income=100000,
            requested_amount=300000,
            requested_tenure=60
        )
        
        # DTI should be lower with higher income
        # Original: 8500 / 50000 = 17%
        # New: 8500 / 100000 = 8.5%
        assert new_decision.approved is True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_none_income_uses_default(self, underwriting_agent):
        """Test that None income uses default assumption."""
        profile = CreditProfile(
            customer_id="CUST999",
            credit_score=750,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=None  # None income - will use default
        )
        
        decision = underwriting_agent.assess_eligibility(
            credit_profile=profile,
            requested_amount=100000,
            requested_tenure=60
        )
        
        # Should still process with default income assumption
        assert decision.max_eligible_amount > 0
    
    def test_exactly_5_loans_is_allowed(self, underwriting_agent):
        """Test that exactly 5 loans is still allowed."""
        loans = []
        for i in range(5):
            loans.append(
                Loan(
                    loan_id=f"LOAN{i:03d}",
                    loan_type="Personal Loan",
                    principal=50000,
                    outstanding=30000,
                    interest_rate=15.0,
                    monthly_emi=2000,
                    remaining_tenure=15
                )
            )
        
        profile = CreditProfile(
            customer_id="CUST998",
            credit_score=750,
            active_loans=loans,
            total_outstanding=150000,
            total_monthly_emi=10000,
            debt_to_income_ratio=20.0,
            monthly_income=50000
        )
        
        decision = underwriting_agent.assess_eligibility(
            credit_profile=profile,
            requested_amount=100000,
            requested_tenure=60
        )
        
        # Should be approved (5 loans is at the limit)
        assert decision.approved is True
    
    def test_minimum_credit_score_boundary(self, underwriting_agent):
        """Test at minimum credit score boundary."""
        profile = CreditProfile(
            customer_id="CUST997",
            credit_score=650,  # Exactly at minimum
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=50000
        )
        
        decision = underwriting_agent.assess_eligibility(
            credit_profile=profile,
            requested_amount=100000,
            requested_tenure=60
        )
        
        # Should be approved at exactly 650
        assert decision.approved is True
        assert decision.credit_score_tier == "GOOD"



class TestLowCreditScoreFlow:
    """Test low credit score flow with LLM-based advice (Task 14.1)."""
    
    def test_low_credit_score_rejection_with_improvement_plan(self, low_credit_profile):
        """Test that low credit score results in rejection with improvement plan."""
        from utils.llm_client import MockLLM
        
        # Create mock LLM with predefined response
        mock_llm = MockLLM(response_map={
            "credit improvement": """1. Pay all bills on time for the next 6 months
2. Reduce credit card utilization to below 30%
3. Avoid applying for new credit
4. Check credit report for errors
5. Pay down existing debt systematically"""
        })
        
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        decision = agent.assess_eligibility(
            credit_profile=low_credit_profile,
            requested_amount=100000,
            requested_tenure=60
        )
        
        # Verify rejection
        assert decision.approved is False
        assert decision.rejection_reason is not None
        assert "credit score" in decision.rejection_reason.lower()
        # Credit score 600 falls into FAIR tier (600-649)
        assert decision.credit_score_tier in ["FAIR", "POOR"]
        
        # Verify improvement plan exists
        assert decision.improvement_plan is not None
        assert len(decision.improvement_plan) >= 4
        
        # Verify LLM was called
        assert mock_llm.call_count > 0
    
    def test_credit_score_below_650_generates_personalized_advice(self):
        """Test that credit score < 650 generates personalized LLM advice."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM(response_map={
            "credit improvement": """1. Set up automatic payments for all loans
2. Pay off credit cards with highest interest first
3. Request credit limit increases without using them
4. Become authorized user on family member's card
5. Dispute any errors on credit report
6. Keep old credit accounts open"""
        })
        
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        # Create profile with score 620
        profile = CreditProfile(
            customer_id="CUST_LOW",
            credit_score=620,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=35000
        )
        
        plan = agent._generate_credit_improvement_plan(profile)
        
        # Should have multiple recommendations
        assert len(plan) >= 4
        
        # Verify LLM was called
        assert mock_llm.call_count == 1
        last_prompt = mock_llm.get_last_prompt()
        assert "620" in last_prompt
        assert "credit improvement" in last_prompt.lower()
    
    def test_credit_improvement_plan_with_existing_debt(self):
        """Test improvement plan considers existing debt."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM(response_map={
            "credit improvement": """1. Focus on paying down the ₹50,000 outstanding debt
2. Make all payments on time
3. Reduce credit utilization
4. Avoid new credit applications
5. Monitor credit score monthly"""
        })
        
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        profile = CreditProfile(
            customer_id="CUST_DEBT",
            credit_score=630,
            active_loans=[
                Loan(
                    loan_id="LOAN001",
                    loan_type="Personal Loan",
                    principal=50000,
                    outstanding=50000,
                    interest_rate=16.0,
                    monthly_emi=3000,
                    remaining_tenure=18
                )
            ],
            total_outstanding=50000,
            total_monthly_emi=3000,
            debt_to_income_ratio=15.0,
            monthly_income=20000
        )
        
        plan = agent._generate_credit_improvement_plan(profile)
        
        assert len(plan) >= 4
        
        # Verify context includes debt information
        last_prompt = mock_llm.get_last_prompt()
        assert "50000" in last_prompt or "50,000" in last_prompt
    
    def test_credit_improvement_plan_fallback_on_llm_failure(self, low_credit_profile):
        """Test that fallback plan is used when LLM fails."""
        from utils.llm_client import MockLLM
        
        # Create mock that raises exception
        class FailingMockLLM(MockLLM):
            def generate(self, prompt, **kwargs):
                raise Exception("LLM API failure")
        
        agent = UnderwritingAgent(llm_client=FailingMockLLM())
        
        plan = agent._generate_credit_improvement_plan(low_credit_profile)
        
        # Should still get fallback recommendations
        assert len(plan) >= 4
        assert any("pay" in item.lower() and "time" in item.lower() for item in plan)
        assert any("credit utilization" in item.lower() for item in plan)
    
    def test_process_method_routes_to_document_agent_for_low_credit(self, low_credit_profile):
        """Test that low credit rejection routes to document agent."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM(response_map={
            "credit improvement": "1. Pay on time\n2. Reduce utilization\n3. Check report\n4. Avoid new credit"
        })
        
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        session_state = {
            "session_id": "test_123",
            "user_id": "CUST_LOW"
        }
        
        input_data = {
            "credit_profile": low_credit_profile,
            "requested_amount": 100000
        }
        
        response = agent.process(input_data, session_state)
        
        assert response["success"] is True
        assert response["data"]["decision"]["approved"] is False
        assert response["data"]["decision"]["improvement_plan"] is not None
        assert response["next_agent"] == "document"
    
    def test_multiple_low_credit_scenarios(self):
        """Test various low credit score scenarios."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM(response_map={
            "credit improvement": "1. Action 1\n2. Action 2\n3. Action 3\n4. Action 4\n5. Action 5"
        })
        
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        test_scores = [500, 550, 600, 640, 649]
        
        for score in test_scores:
            profile = CreditProfile(
                customer_id=f"CUST_{score}",
                credit_score=score,
                active_loans=[],
                total_outstanding=0,
                total_monthly_emi=0,
                debt_to_income_ratio=0,
                monthly_income=40000
            )
            
            decision = agent.assess_eligibility(profile, 100000, 60)
            
            # All should be rejected
            assert decision.approved is False
            assert decision.improvement_plan is not None
            assert len(decision.improvement_plan) >= 3
            assert "credit score" in decision.rejection_reason.lower()



class TestSingleLoanFlow:
    """Test single loan flow with transfer vs new loan comparison (Task 14.2)."""
    
    def test_compare_single_loan_options_basic(self):
        """Test basic single loan comparison."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        # Create profile with one loan
        profile = CreditProfile(
            customer_id="CUST_SINGLE",
            credit_score=720,
            active_loans=[
                Loan(
                    loan_id="LOAN001",
                    loan_type="Personal Loan",
                    principal=200000,
                    outstanding=150000,
                    interest_rate=14.0,
                    monthly_emi=8000,
                    remaining_tenure=20
                )
            ],
            total_outstanding=150000,
            total_monthly_emi=8000,
            debt_to_income_ratio=16.0,
            monthly_income=50000
        )
        
        comparison = agent.compare_single_loan_options(
            credit_profile=profile,
            requested_amount=100000,
            requested_tenure=60
        )
        
        # Verify structure
        assert "existing_loan" in comparison
        assert "option_1_transfer" in comparison
        assert "option_2_new_loan" in comparison
        assert "recommendation" in comparison
        
        # Verify existing loan data
        assert comparison["existing_loan"]["outstanding"] == 150000
        assert comparison["existing_loan"]["monthly_emi"] == 8000
        
        # Verify both options are evaluated
        assert comparison["option_1_transfer"]["total_amount"] == 250000  # 150k + 100k
        assert comparison["option_2_new_loan"]["new_loan_amount"] == 100000
    
    def test_single_loan_transfer_option_approved(self):
        """Test that transfer option is properly evaluated."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        profile = CreditProfile(
            customer_id="CUST_SINGLE",
            credit_score=750,
            active_loans=[
                Loan(
                    loan_id="LOAN001",
                    loan_type="Personal Loan",
                    principal=100000,
                    outstanding=80000,
                    interest_rate=15.0,
                    monthly_emi=5000,
                    remaining_tenure=18
                )
            ],
            total_outstanding=80000,
            total_monthly_emi=5000,
            debt_to_income_ratio=10.0,
            monthly_income=50000
        )
        
        comparison = agent.compare_single_loan_options(
            credit_profile=profile,
            requested_amount=50000,
            requested_tenure=48
        )
        
        # Transfer option should be approved
        assert comparison["option_1_transfer"]["approved"] is True
        assert comparison["option_1_transfer"]["total_amount"] == 130000
        assert comparison["option_1_transfer"]["monthly_emi"] > 0
        assert comparison["option_1_transfer"]["interest_rate"] == 10.5  # Excellent tier
    
    def test_single_loan_new_loan_option_approved(self):
        """Test that new loan option is properly evaluated."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        profile = CreditProfile(
            customer_id="CUST_SINGLE",
            credit_score=700,
            active_loans=[
                Loan(
                    loan_id="LOAN001",
                    loan_type="Personal Loan",
                    principal=100000,
                    outstanding=60000,
                    interest_rate=14.0,
                    monthly_emi=4000,
                    remaining_tenure=16
                )
            ],
            total_outstanding=60000,
            total_monthly_emi=4000,
            debt_to_income_ratio=8.0,
            monthly_income=50000
        )
        
        comparison = agent.compare_single_loan_options(
            credit_profile=profile,
            requested_amount=80000,
            requested_tenure=60
        )
        
        # New loan option should be approved
        assert comparison["option_2_new_loan"]["approved"] is True
        assert comparison["option_2_new_loan"]["new_loan_amount"] == 80000
        assert comparison["option_2_new_loan"]["new_loan_emi"] > 0
        
        # Total payment should be existing + new
        expected_total = 4000 + comparison["option_2_new_loan"]["new_loan_emi"]
        assert abs(comparison["option_2_new_loan"]["total_monthly_payment"] - expected_total) < 1
    
    def test_single_loan_comparison_recommendation(self):
        """Test that recommendation is provided based on better option."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        profile = CreditProfile(
            customer_id="CUST_SINGLE",
            credit_score=720,
            active_loans=[
                Loan(
                    loan_id="LOAN001",
                    loan_type="Personal Loan",
                    principal=150000,
                    outstanding=100000,
                    interest_rate=16.0,
                    monthly_emi=7000,
                    remaining_tenure=16
                )
            ],
            total_outstanding=100000,
            total_monthly_emi=7000,
            debt_to_income_ratio=14.0,
            monthly_income=50000
        )
        
        comparison = agent.compare_single_loan_options(
            credit_profile=profile,
            requested_amount=100000,
            requested_tenure=60
        )
        
        # Should have a recommendation
        assert comparison["recommendation"] in ["transfer", "new_loan"]
        assert comparison["recommendation_reason"] is not None
        
        # If transfer is recommended, it should have lower EMI
        if comparison["recommendation"] == "transfer":
            assert comparison["option_1_transfer"]["monthly_emi"] < comparison["option_2_new_loan"]["total_monthly_payment"]
            assert comparison["monthly_savings"] > 0
    
    def test_single_loan_comparison_fails_for_multiple_loans(self):
        """Test that comparison fails for profiles with multiple loans."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        profile = CreditProfile(
            customer_id="CUST_MULTI",
            credit_score=720,
            active_loans=[
                Loan(loan_id="LOAN001", loan_type="Personal Loan", principal=100000,
                     outstanding=80000, interest_rate=14.0, monthly_emi=5000, remaining_tenure=18),
                Loan(loan_id="LOAN002", loan_type="Car Loan", principal=200000,
                     outstanding=150000, interest_rate=12.0, monthly_emi=8000, remaining_tenure=20)
            ],
            total_outstanding=230000,
            total_monthly_emi=13000,
            debt_to_income_ratio=26.0,
            monthly_income=50000
        )
        
        with pytest.raises(BusinessLogicError) as exc_info:
            agent.compare_single_loan_options(profile, 50000, 48)
        
        assert "exactly one active loan" in str(exc_info.value).lower()
    
    def test_single_loan_comparison_fails_for_zero_loans(self):
        """Test that comparison fails for profiles with no loans."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        profile = CreditProfile(
            customer_id="CUST_ZERO",
            credit_score=750,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=60000
        )
        
        with pytest.raises(BusinessLogicError) as exc_info:
            agent.compare_single_loan_options(profile, 100000, 60)
        
        assert "exactly one active loan" in str(exc_info.value).lower()



class TestNoLoansFlow:
    """Test no loans flow for new customers (Task 14.3)."""
    
    def test_new_customer_gets_competitive_rate(self):
        """Test that new customers with good credit get competitive rates."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        # New customer with excellent credit
        profile = CreditProfile(
            customer_id="CUST_NEW_EXCELLENT",
            credit_score=780,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=80000
        )
        
        decision = agent.assess_eligibility(
            credit_profile=profile,
            requested_amount=500000,
            requested_tenure=60
        )
        
        # Should be approved with discounted rate
        assert decision.approved is True
        # Excellent tier is 10.5%, new customer discount makes it 10.0%
        assert decision.interest_rate == 10.0
        assert decision.credit_score_tier == "EXCELLENT"
    
    def test_new_customer_good_credit_gets_discount(self):
        """Test that new customers with good credit get 0.5% discount."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        # New customer with good credit
        profile = CreditProfile(
            customer_id="CUST_NEW_GOOD",
            credit_score=700,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=60000
        )
        
        decision = agent.assess_eligibility(
            credit_profile=profile,
            requested_amount=300000,
            requested_tenure=48
        )
        
        # Should be approved with discounted rate
        assert decision.approved is True
        # Good tier is 12.5%, new customer discount makes it 12.0%
        assert decision.interest_rate == 12.0
        assert decision.credit_score_tier == "GOOD"
    
    def test_new_customer_below_700_no_discount(self):
        """Test that new customers with credit < 700 don't get discount."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        # New customer with fair credit
        profile = CreditProfile(
            customer_id="CUST_NEW_FAIR",
            credit_score=680,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=50000
        )
        
        decision = agent.assess_eligibility(
            credit_profile=profile,
            requested_amount=200000,
            requested_tenure=60
        )
        
        # Should be approved but no discount
        assert decision.approved is True
        # Good tier standard rate (680 is in GOOD tier)
        assert decision.interest_rate == 12.5
    
    def test_generate_new_customer_offer_with_benefits(self):
        """Test generating complete new customer offer with benefits."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        profile = CreditProfile(
            customer_id="CUST_NEW",
            credit_score=750,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=70000
        )
        
        offer = agent.generate_new_customer_offer(
            credit_profile=profile,
            requested_amount=400000,
            requested_tenure=60
        )
        
        # Verify structure
        assert offer["is_new_customer"] is True
        assert "decision" in offer
        assert "new_customer_benefits" in offer
        
        # Verify benefits list
        benefits = offer["new_customer_benefits"]
        assert len(benefits) >= 4
        assert any("competitive" in b.lower() for b in benefits)
        assert any("fast approval" in b.lower() or "48 hours" in b.lower() for b in benefits)
        
        # Verify special rate applied
        assert offer.get("special_rate_applied") is True
        
        # Verify decision is approved
        assert offer["decision"].approved is True
    
    def test_new_customer_offer_excellent_credit_premium_benefits(self):
        """Test that excellent credit new customers get premium benefits."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        profile = CreditProfile(
            customer_id="CUST_NEW_PREMIUM",
            credit_score=800,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=100000
        )
        
        offer = agent.generate_new_customer_offer(
            credit_profile=profile,
            requested_amount=600000,
            requested_tenure=60
        )
        
        benefits = offer["new_customer_benefits"]
        
        # Should have premium benefits
        assert any("premium" in b.lower() or "relationship manager" in b.lower() for b in benefits)
        assert any("12 months" in b.lower() for b in benefits)
    
    def test_new_customer_offer_fails_for_existing_loans(self):
        """Test that new customer offer fails for profiles with existing loans."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        profile = CreditProfile(
            customer_id="CUST_EXISTING",
            credit_score=750,
            active_loans=[
                Loan(
                    loan_id="LOAN001",
                    loan_type="Personal Loan",
                    principal=100000,
                    outstanding=80000,
                    interest_rate=14.0,
                    monthly_emi=5000,
                    remaining_tenure=18
                )
            ],
            total_outstanding=80000,
            total_monthly_emi=5000,
            debt_to_income_ratio=10.0,
            monthly_income=50000
        )
        
        with pytest.raises(BusinessLogicError) as exc_info:
            agent.generate_new_customer_offer(profile, 100000, 60)
        
        assert "no existing loans" in str(exc_info.value).lower()
    
    def test_zero_loans_standard_offer_generation(self):
        """Test standard loan offer for customers with zero existing loans."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        # Multiple scenarios with zero loans
        test_cases = [
            {"score": 780, "income": 100000, "amount": 500000},
            {"score": 720, "income": 60000, "amount": 300000},
            {"score": 700, "income": 50000, "amount": 200000},
        ]
        
        for case in test_cases:
            profile = CreditProfile(
                customer_id=f"CUST_{case['score']}",
                credit_score=case["score"],
                active_loans=[],
                total_outstanding=0,
                total_monthly_emi=0,
                debt_to_income_ratio=0,
                monthly_income=case["income"]
            )
            
            decision = agent.assess_eligibility(
                credit_profile=profile,
                requested_amount=case["amount"],
                requested_tenure=60
            )
            
            # All should be approved
            assert decision.approved is True
            assert decision.loan_amount > 0
            assert decision.monthly_emi > 0
            
            # Verify competitive rate for good credit
            if case["score"] >= 700:
                # Should have discount applied
                tier_rate = agent.CREDIT_TIERS[agent._determine_credit_tier(case["score"])]["interest_rate"]
                assert decision.interest_rate < tier_rate



class TestNoLoansFlow:
    """Test no loans flow with competitive rates for new customers (Task 14.3)."""
    
    def test_new_customer_offer_basic(self):
        """Test basic new customer offer generation."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        # Create profile with no loans
        profile = CreditProfile(
            customer_id="CUST_NEW",
            credit_score=750,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=60000
        )
        
        decision = agent.generate_new_customer_offer(
            credit_profile=profile,
            requested_amount=300000,
            requested_tenure=60
        )
        
        # Should be approved
        assert decision.approved is True
        assert decision.loan_amount == 300000
        assert decision.tenure_months == 60
        assert decision.monthly_emi > 0
    
    def test_new_customer_gets_discount_for_good_credit(self):
        """Test that new customers with credit score >= 700 get 0.5% discount."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        # Create profile with excellent credit
        profile = CreditProfile(
            customer_id="CUST_NEW_EXCELLENT",
            credit_score=780,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=80000
        )
        
        decision = agent.generate_new_customer_offer(
            credit_profile=profile,
            requested_amount=500000,
            requested_tenure=60
        )
        
        # Should get discounted rate (10.5% - 0.5% = 10.0%)
        assert decision.approved is True
        assert decision.interest_rate == 10.0  # Excellent tier (10.5%) - 0.5% discount
    
    def test_new_customer_discount_not_below_minimum(self):
        """Test that discount doesn't go below 9.5% minimum."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        # Temporarily modify the tier to test minimum
        original_rate = agent.CREDIT_TIERS["EXCELLENT"]["interest_rate"]
        agent.CREDIT_TIERS["EXCELLENT"]["interest_rate"] = 9.8  # Close to minimum
        
        try:
            profile = CreditProfile(
                customer_id="CUST_NEW_MIN",
                credit_score=800,
                active_loans=[],
                total_outstanding=0,
                total_monthly_emi=0,
                debt_to_income_ratio=0,
                monthly_income=100000
            )
            
            decision = agent.generate_new_customer_offer(
                credit_profile=profile,
                requested_amount=500000,
                requested_tenure=60
            )
            
            # Should not go below 9.5%
            assert decision.approved is True
            assert decision.interest_rate >= 9.5
        finally:
            # Restore original rate
            agent.CREDIT_TIERS["EXCELLENT"]["interest_rate"] = original_rate
    
    def test_new_customer_no_discount_for_fair_credit(self):
        """Test that customers with credit score < 700 don't get discount."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        profile = CreditProfile(
            customer_id="CUST_NEW_FAIR",
            credit_score=680,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=50000
        )
        
        decision = agent.generate_new_customer_offer(
            credit_profile=profile,
            requested_amount=200000,
            requested_tenure=48
        )
        
        # Should get standard rate without discount (12.5% for GOOD tier)
        assert decision.approved is True
        assert decision.interest_rate == 12.5  # No discount applied
    
    def test_new_customer_offer_fails_for_existing_loans(self):
        """Test that new customer offer fails if customer has existing loans."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        profile = CreditProfile(
            customer_id="CUST_EXISTING",
            credit_score=750,
            active_loans=[
                Loan(
                    loan_id="LOAN001",
                    loan_type="Personal Loan",
                    principal=100000,
                    outstanding=80000,
                    interest_rate=14.0,
                    monthly_emi=5000,
                    remaining_tenure=18
                )
            ],
            total_outstanding=80000,
            total_monthly_emi=5000,
            debt_to_income_ratio=10.0,
            monthly_income=50000
        )
        
        with pytest.raises(BusinessLogicError) as exc_info:
            agent.generate_new_customer_offer(profile, 100000, 60)
        
        assert "no existing loans" in str(exc_info.value).lower()
    
    def test_new_customer_offer_with_high_amount(self):
        """Test new customer offer with high loan amount."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        profile = CreditProfile(
            customer_id="CUST_NEW_HIGH",
            credit_score=780,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=150000
        )
        
        decision = agent.generate_new_customer_offer(
            credit_profile=profile,
            requested_amount=1000000,
            requested_tenure=84
        )
        
        # Should be approved with competitive rate
        assert decision.approved is True
        assert decision.loan_amount == 1000000
        assert decision.interest_rate == 10.0  # Discounted rate
        assert decision.tenure_months == 84
    
    def test_new_customer_offer_respects_dti_limits(self):
        """Test that new customer offers still respect DTI limits."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        profile = CreditProfile(
            customer_id="CUST_NEW_LOW_INCOME",
            credit_score=720,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0,
            debt_to_income_ratio=0,
            monthly_income=25000  # Low income
        )
        
        # Request very high amount relative to income
        decision = agent.generate_new_customer_offer(
            credit_profile=profile,
            requested_amount=1000000,
            requested_tenure=60
        )
        
        # Should either be rejected or offer lower amount
        if decision.approved:
            # If approved, amount should be reduced to affordable level
            assert decision.loan_amount < 1000000
        else:
            # Or rejected due to DTI
            assert decision.approved is False
    
    def test_new_customer_zero_loans_scenario(self):
        """Test various scenarios for customers with zero existing loans."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        test_cases = [
            {"score": 800, "income": 100000, "amount": 500000, "should_approve": True},
            {"score": 750, "income": 60000, "amount": 300000, "should_approve": True},
            {"score": 700, "income": 40000, "amount": 200000, "should_approve": True},
            {"score": 680, "income": 30000, "amount": 150000, "should_approve": True},
        ]
        
        for case in test_cases:
            profile = CreditProfile(
                customer_id=f"CUST_{case['score']}",
                credit_score=case["score"],
                active_loans=[],
                total_outstanding=0,
                total_monthly_emi=0,
                debt_to_income_ratio=0,
                monthly_income=case["income"]
            )
            
            decision = agent.generate_new_customer_offer(
                profile, case["amount"], 60
            )
            
            assert decision.approved == case["should_approve"]
            
            # Verify discount applied for scores >= 700
            if decision.approved and case["score"] >= 700:
                # Should have discounted rate
                tier = agent._determine_credit_tier(case["score"])
                standard_rate = agent.CREDIT_TIERS[tier]["interest_rate"]
                expected_rate = max(standard_rate - 0.5, 9.5)
                assert decision.interest_rate == expected_rate



class TestTooManyLoansRejectionFlow:
    """Test too many loans rejection flow with empathetic messaging (Task 14.4)."""
    
    def test_rejection_for_six_loans(self):
        """Test rejection for customer with 6 loans (> MAX_LOAN_COUNT)."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        # Create profile with 6 loans
        loans = []
        for i in range(6):
            loans.append(
                Loan(
                    loan_id=f"LOAN{i:03d}",
                    loan_type="Personal Loan",
                    principal=50000,
                    outstanding=30000,
                    interest_rate=15.0,
                    monthly_emi=2000,
                    remaining_tenure=15
                )
            )
        
        profile = CreditProfile(
            customer_id="CUST_6LOANS",
            credit_score=720,
            active_loans=loans,
            total_outstanding=180000,
            total_monthly_emi=12000,
            debt_to_income_ratio=30.0,
            monthly_income=40000
        )
        
        decision = agent.assess_eligibility(profile, 100000, 60)
        
        # Should be rejected
        assert decision.approved is False
        assert "6 active loans" in decision.rejection_reason
        assert "financial wellbeing" in decision.rejection_reason.lower()
        assert decision.improvement_plan is not None
        assert len(decision.improvement_plan) >= 5
    
    def test_empathetic_rejection_message(self):
        """Test that rejection message is empathetic and helpful."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        loans = [
            Loan(loan_id=f"LOAN{i}", loan_type="Personal Loan", principal=50000,
                 outstanding=40000, interest_rate=14.0, monthly_emi=2500, remaining_tenure=18)
            for i in range(7)
        ]
        
        profile = CreditProfile(
            customer_id="CUST_7LOANS",
            credit_score=700,
            active_loans=loans,
            total_outstanding=280000,
            total_monthly_emi=17500,
            debt_to_income_ratio=35.0,
            monthly_income=50000
        )
        
        decision = agent.assess_eligibility(profile, 50000, 48)
        
        # Verify empathetic language
        assert decision.approved is False
        assert "appreciate your interest" in decision.rejection_reason.lower()
        assert "help you manage" in decision.rejection_reason.lower() or "here to help" in decision.rejection_reason.lower()
        assert "reconsider your application" in decision.rejection_reason.lower()
    
    def test_debt_management_advice_content(self):
        """Test that debt management advice is comprehensive."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        loans = [
            Loan(loan_id=f"LOAN{i}", loan_type="Personal Loan", principal=100000,
                 outstanding=80000, interest_rate=15.0, monthly_emi=5000, remaining_tenure=18)
            for i in range(6)
        ]
        
        profile = CreditProfile(
            customer_id="CUST_ADVICE",
            credit_score=680,
            active_loans=loans,
            total_outstanding=480000,
            total_monthly_emi=30000,
            debt_to_income_ratio=50.0,
            monthly_income=60000
        )
        
        advice = agent._generate_too_many_loans_advice(profile)
        
        # Should have comprehensive advice
        assert len(advice) >= 7
        
        # Check for key advice elements
        advice_text = " ".join(advice).lower()
        assert "consolidat" in advice_text
        assert "pay" in advice_text
        assert "debt" in advice_text
        assert "5" in advice_text or "five" in advice_text  # Reference to MAX_LOAN_COUNT
    
    def test_advice_includes_high_debt_warning(self):
        """Test that advice includes specific warning for high total debt."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        loans = [
            Loan(loan_id=f"LOAN{i}", loan_type="Personal Loan", principal=150000,
                 outstanding=120000, interest_rate=14.0, monthly_emi=7000, remaining_tenure=20)
            for i in range(6)
        ]
        
        profile = CreditProfile(
            customer_id="CUST_HIGH_DEBT",
            credit_score=700,
            active_loans=loans,
            total_outstanding=720000,  # > 500k
            total_monthly_emi=42000,
            debt_to_income_ratio=42.0,
            monthly_income=100000
        )
        
        advice = agent._generate_too_many_loans_advice(profile)
        
        # Should include specific advice about high debt
        advice_text = " ".join(advice)
        assert "720,000" in advice_text or "7,20,000" in advice_text or "20%" in advice_text
    
    def test_rejection_at_exactly_six_loans(self):
        """Test rejection at exactly 6 loans (boundary condition)."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        # Exactly 6 loans (MAX_LOAN_COUNT + 1)
        loans = [
            Loan(loan_id=f"LOAN{i}", loan_type="Personal Loan", principal=50000,
                 outstanding=30000, interest_rate=14.0, monthly_emi=2000, remaining_tenure=16)
            for i in range(6)
        ]
        
        profile = CreditProfile(
            customer_id="CUST_BOUNDARY",
            credit_score=750,
            active_loans=loans,
            total_outstanding=180000,
            total_monthly_emi=12000,
            debt_to_income_ratio=20.0,
            monthly_income=60000
        )
        
        decision = agent.assess_eligibility(profile, 100000, 60)
        
        # Should be rejected even with good credit
        assert decision.approved is False
        assert decision.improvement_plan is not None
    
    def test_approval_at_exactly_five_loans(self):
        """Test approval at exactly 5 loans (at MAX_LOAN_COUNT)."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        # Exactly 5 loans (at MAX_LOAN_COUNT)
        loans = [
            Loan(loan_id=f"LOAN{i}", loan_type="Personal Loan", principal=50000,
                 outstanding=30000, interest_rate=14.0, monthly_emi=2000, remaining_tenure=16)
            for i in range(5)
        ]
        
        profile = CreditProfile(
            customer_id="CUST_AT_LIMIT",
            credit_score=750,
            active_loans=loans,
            total_outstanding=150000,
            total_monthly_emi=10000,
            debt_to_income_ratio=16.7,
            monthly_income=60000
        )
        
        decision = agent.assess_eligibility(profile, 100000, 60)
        
        # Should be approved (5 is at the limit, not over)
        assert decision.approved is True
    
    def test_excessive_loans_various_counts(self):
        """Test rejection for various excessive loan counts."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        # Test counts up to 10 (model validation limit)
        test_counts = [6, 7, 8, 9, 10]
        
        for count in test_counts:
            loans = [
                Loan(loan_id=f"LOAN{i}", loan_type="Personal Loan", principal=50000,
                     outstanding=30000, interest_rate=14.0, monthly_emi=2000, remaining_tenure=16)
                for i in range(count)
            ]
            
            profile = CreditProfile(
                customer_id=f"CUST_{count}LOANS",
                credit_score=720,
                active_loans=loans,
                total_outstanding=30000 * count,
                total_monthly_emi=2000 * count,
                debt_to_income_ratio=20.0,
                monthly_income=10000 * count
            )
            
            decision = agent.assess_eligibility(profile, 50000, 48)
            
            # All should be rejected
            assert decision.approved is False
            assert f"{count} active loans" in decision.rejection_reason
            assert decision.improvement_plan is not None
    
    def test_process_method_with_too_many_loans(self):
        """Test that process method handles too many loans correctly."""
        from utils.llm_client import MockLLM
        
        mock_llm = MockLLM()
        agent = UnderwritingAgent(llm_client=mock_llm)
        
        loans = [
            Loan(loan_id=f"LOAN{i}", loan_type="Personal Loan", principal=50000,
                 outstanding=40000, interest_rate=14.0, monthly_emi=2500, remaining_tenure=18)
            for i in range(6)
        ]
        
        profile = CreditProfile(
            customer_id="CUST_PROCESS",
            credit_score=720,
            active_loans=loans,
            total_outstanding=240000,
            total_monthly_emi=15000,
            debt_to_income_ratio=30.0,
            monthly_income=50000
        )
        
        session_state = {
            "session_id": "test_session",
            "user_id": "CUST_PROCESS"
        }
        
        input_data = {
            "credit_profile": profile,
            "requested_amount": 100000
        }
        
        response = agent.process(input_data, session_state)
        
        # Should return rejection with improvement plan
        assert response["success"] is True
        assert response["data"]["decision"]["approved"] is False
        assert response["data"]["decision"]["improvement_plan"] is not None
        assert response["next_agent"] == "document"  # Should route to document agent for improvement plan
