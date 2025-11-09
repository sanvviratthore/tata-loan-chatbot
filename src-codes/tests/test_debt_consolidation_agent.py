"""
Unit tests for Debt Consolidation Agent
"""

import pytest
from datetime import datetime

from agents.debt_consolidation_agent import DebtConsolidationAgent
from agents.base_agent import ValidationError, BusinessLogicError
from schemas.models import Loan, CreditProfile, ConsolidationOffer


class TestDebtConsolidationAgent:
    """Test suite for DebtConsolidationAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance for testing."""
        return DebtConsolidationAgent()
    
    @pytest.fixture
    def sample_loans_2(self):
        """Create sample data with 2 loans."""
        return [
            Loan(
                loan_id="LOAN001",
                loan_type="Personal Loan",
                lender="Bank A",
                principal=200000,
                outstanding=150000,
                interest_rate=14.5,
                monthly_emi=8500,
                remaining_tenure=18
            ),
            Loan(
                loan_id="LOAN002",
                loan_type="Credit Card",
                lender="Bank B",
                principal=50000,
                outstanding=50000,
                interest_rate=18.0,
                monthly_emi=5000,
                remaining_tenure=12
            )
        ]
    
    @pytest.fixture
    def sample_loans_3(self):
        """Create sample data with 3 loans."""
        return [
            Loan(
                loan_id="LOAN001",
                loan_type="Personal Loan",
                lender="Bank A",
                principal=200000,
                outstanding=150000,
                interest_rate=14.5,
                monthly_emi=8500,
                remaining_tenure=18
            ),
            Loan(
                loan_id="LOAN002",
                loan_type="Credit Card",
                lender="Bank B",
                principal=50000,
                outstanding=50000,
                interest_rate=18.0,
                monthly_emi=5000,
                remaining_tenure=12
            ),
            Loan(
                loan_id="LOAN003",
                loan_type="Auto Loan",
                lender="Bank C",
                principal=300000,
                outstanding=100000,
                interest_rate=12.0,
                monthly_emi=4500,
                remaining_tenure=24
            )
        ]
    
    @pytest.fixture
    def sample_loans_5(self):
        """Create sample data with 5 loans."""
        return [
            Loan(
                loan_id="LOAN001",
                loan_type="Personal Loan",
                lender="Bank A",
                principal=200000,
                outstanding=150000,
                interest_rate=14.5,
                monthly_emi=8500,
                remaining_tenure=18
            ),
            Loan(
                loan_id="LOAN002",
                loan_type="Credit Card",
                lender="Bank B",
                principal=50000,
                outstanding=50000,
                interest_rate=18.0,
                monthly_emi=5000,
                remaining_tenure=12
            ),
            Loan(
                loan_id="LOAN003",
                loan_type="Auto Loan",
                lender="Bank C",
                principal=300000,
                outstanding=100000,
                interest_rate=12.0,
                monthly_emi=4500,
                remaining_tenure=24
            ),
            Loan(
                loan_id="LOAN004",
                loan_type="Personal Loan",
                lender="Bank D",
                principal=100000,
                outstanding=75000,
                interest_rate=15.0,
                monthly_emi=3500,
                remaining_tenure=20
            ),
            Loan(
                loan_id="LOAN005",
                loan_type="Consumer Loan",
                lender="Bank E",
                principal=80000,
                outstanding=60000,
                interest_rate=16.0,
                monthly_emi=3000,
                remaining_tenure=15
            )
        ]
    
    @pytest.fixture
    def credit_profile_2_loans(self, sample_loans_2):
        """Create credit profile with 2 loans."""
        return CreditProfile(
            customer_id="CUST001",
            credit_score=720,
            active_loans=sample_loans_2,
            total_outstanding=200000,
            total_monthly_emi=13500,
            debt_to_income_ratio=35.0,
            monthly_income=75000
        )
    
    @pytest.fixture
    def credit_profile_3_loans(self, sample_loans_3):
        """Create credit profile with 3 loans."""
        return CreditProfile(
            customer_id="CUST002",
            credit_score=680,
            active_loans=sample_loans_3,
            total_outstanding=300000,
            total_monthly_emi=18000,
            debt_to_income_ratio=40.0,
            monthly_income=80000
        )
    
    @pytest.fixture
    def credit_profile_5_loans(self, sample_loans_5):
        """Create credit profile with 5 loans."""
        return CreditProfile(
            customer_id="CUST003",
            credit_score=750,
            active_loans=sample_loans_5,
            total_outstanding=435000,
            total_monthly_emi=24500,
            debt_to_income_ratio=45.0,
            monthly_income=100000
        )
    
    def test_agent_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent.agent_name == "debt_consolidation_agent"
        assert agent.min_loans_for_consolidation == 2
        assert agent.max_loans_for_consolidation == 5
        assert agent.interest_rate_reduction == 2.0
        assert agent.min_interest_rate == 9.5
    
    def test_validate_input_success(self, agent, credit_profile_2_loans):
        """Test input validation with valid data."""
        input_data = {"credit_profile": credit_profile_2_loans}
        assert agent.validate_input(input_data) is True
    
    def test_validate_input_missing_credit_profile(self, agent):
        """Test validation fails when credit profile is missing."""
        input_data = {}
        with pytest.raises(ValidationError) as exc_info:
            agent.validate_input(input_data)
        # Should raise validation error (either for missing input or missing credit profile)
        assert "required" in str(exc_info.value).lower()
    
    def test_validate_input_too_few_loans(self, agent):
        """Test validation fails with less than 2 loans."""
        single_loan = [
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
        ]
        credit_profile = CreditProfile(
            customer_id="CUST001",
            credit_score=720,
            active_loans=single_loan,
            total_outstanding=150000,
            total_monthly_emi=8500
        )
        input_data = {"credit_profile": credit_profile}
        
        with pytest.raises(BusinessLogicError) as exc_info:
            agent.validate_input(input_data)
        assert "at least 2 loans" in str(exc_info.value).lower()
    
    def test_validate_input_too_many_loans(self, agent):
        """Test validation fails with more than 5 loans."""
        # Create 6 loans
        many_loans = [
            Loan(
                loan_id=f"LOAN{i:03d}",
                loan_type="Personal Loan",
                lender=f"Bank {chr(65+i)}",
                principal=100000,
                outstanding=50000,
                interest_rate=14.0,
                monthly_emi=3000,
                remaining_tenure=18
            )
            for i in range(6)
        ]
        credit_profile = CreditProfile(
            customer_id="CUST001",
            credit_score=720,
            active_loans=many_loans,
            total_outstanding=300000,
            total_monthly_emi=18000
        )
        input_data = {"credit_profile": credit_profile}
        
        with pytest.raises(BusinessLogicError) as exc_info:
            agent.validate_input(input_data)
        assert "cannot consolidate more than 5 loans" in str(exc_info.value).lower()
    
    def test_generate_consolidation_offer_2_loans(self, agent, sample_loans_2):
        """Test consolidation offer generation with 2 loans."""
        offer = agent.generate_consolidation_offer(
            active_loans=sample_loans_2,
            credit_score=720,
            customer_id="CUST001"
        )
        
        # Verify offer structure
        assert isinstance(offer, ConsolidationOffer)
        assert offer.customer_id == "CUST001"
        assert offer.consolidated_amount == 200000  # 150000 + 50000
        assert offer.current_total_emi == 13500  # 8500 + 5000
        assert len(offer.loans_being_consolidated) == 2
        
        # Verify interest rate reduction
        assert offer.new_interest_rate < 15.5  # Should be less than weighted average
        assert offer.new_interest_rate >= agent.min_interest_rate
        
        # Verify savings
        assert offer.monthly_savings > 0  # Should have positive savings
        assert offer.new_monthly_emi < offer.current_total_emi
        
        # Verify comparison table exists
        assert "comparison_metrics" in offer.comparison_table
        assert "current_loans" in offer.comparison_table
        assert "consolidated_loan" in offer.comparison_table
    
    def test_generate_consolidation_offer_3_loans(self, agent, sample_loans_3):
        """Test consolidation offer generation with 3 loans."""
        offer = agent.generate_consolidation_offer(
            active_loans=sample_loans_3,
            credit_score=680,
            customer_id="CUST002"
        )
        
        # Verify offer structure
        assert isinstance(offer, ConsolidationOffer)
        assert offer.customer_id == "CUST002"
        assert offer.consolidated_amount == 300000  # 150000 + 50000 + 100000
        assert offer.current_total_emi == 18000  # 8500 + 5000 + 4500
        assert len(offer.loans_being_consolidated) == 3
        
        # Verify monthly savings (should always be positive due to lower EMI)
        assert offer.monthly_savings > 0
        
        # Note: Total interest savings can be negative when extending tenure
        # The benefit is lower monthly EMI, not necessarily lower total interest
        # This is a valid consolidation scenario for cash flow management
        
        # Verify tenure is reasonable
        assert offer.new_tenure_months >= 24  # At least max of existing tenures
        assert offer.new_tenure_months <= 84  # Not more than 7 years
    
    def test_generate_consolidation_offer_5_loans(self, agent, sample_loans_5):
        """Test consolidation offer generation with 5 loans."""
        offer = agent.generate_consolidation_offer(
            active_loans=sample_loans_5,
            credit_score=750,
            customer_id="CUST003"
        )
        
        # Verify offer structure
        assert isinstance(offer, ConsolidationOffer)
        assert offer.customer_id == "CUST003"
        assert offer.consolidated_amount == 435000
        assert offer.current_total_emi == 24500
        assert len(offer.loans_being_consolidated) == 5
        
        # Verify excellent credit score gets better rate
        # With score 750, should get additional 0.5% reduction
        assert offer.new_interest_rate <= 13.0  # Should be quite low
        
        # Verify monthly savings (primary benefit of consolidation)
        assert offer.monthly_savings > 0
        
        # Note: Total interest savings can be negative when extending tenure
        # The main benefit is reduced monthly burden and simplified payments
    
    def test_process_method_success(self, agent, credit_profile_2_loans):
        """Test process method with valid input."""
        input_data = {"credit_profile": credit_profile_2_loans}
        session_state = {"session_id": "test_session"}
        
        result = agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert "data" in result
        assert result["next_agent"] == "sales"
        assert "message" in result
        
        # Verify data structure
        offer_data = result["data"]
        assert offer_data["customer_id"] == "CUST001"
        assert offer_data["consolidated_amount"] == 200000
        assert offer_data["monthly_savings"] > 0
    
    def test_process_method_with_dict_credit_profile(self, agent, credit_profile_2_loans):
        """Test process method accepts credit profile as dict."""
        input_data = {"credit_profile": credit_profile_2_loans.model_dump()}
        session_state = {"session_id": "test_session"}
        
        result = agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert result["data"]["customer_id"] == "CUST001"
    
    def test_calculate_consolidated_terms(self, agent, sample_loans_2):
        """Test consolidated terms calculation."""
        terms = agent._calculate_consolidated_terms(
            total_outstanding=200000,
            credit_score=720,
            active_loans=sample_loans_2,
            current_avg_rate=15.5
        )
        
        assert "interest_rate" in terms
        assert "tenure_months" in terms
        
        # Interest rate should be reduced by 2%
        assert terms["interest_rate"] <= 13.5  # 15.5 - 2.0
        assert terms["interest_rate"] >= agent.min_interest_rate
        
        # Tenure should be at least max of existing
        assert terms["tenure_months"] >= 18
        assert terms["tenure_months"] <= 84
    
    def test_calculate_consolidated_terms_excellent_credit(self, agent, sample_loans_2):
        """Test terms calculation with excellent credit score."""
        terms = agent._calculate_consolidated_terms(
            total_outstanding=200000,
            credit_score=780,
            active_loans=sample_loans_2,
            current_avg_rate=15.5
        )
        
        # Should get additional 0.5% reduction for score >= 750
        assert terms["interest_rate"] <= 13.0  # 15.5 - 2.0 - 0.5
    
    def test_calculate_consolidated_terms_poor_credit(self, agent, sample_loans_2):
        """Test terms calculation with poor credit score."""
        terms = agent._calculate_consolidated_terms(
            total_outstanding=200000,
            credit_score=640,
            active_loans=sample_loans_2,
            current_avg_rate=15.5
        )
        
        # Should get 1% penalty for score < 650
        assert terms["interest_rate"] >= 14.5  # 15.5 - 2.0 + 1.0
    
    def test_calculate_current_total_interest(self, agent, sample_loans_2):
        """Test calculation of current total interest."""
        total_interest = agent._calculate_current_total_interest(sample_loans_2)
        
        # Loan 1: 8500 * 18 - 150000 = 3000
        # Loan 2: 5000 * 12 - 50000 = 10000
        # Total: 13000
        assert total_interest == 13000.0
    
    def test_create_comparison_table(self, agent, sample_loans_2):
        """Test comparison table creation."""
        comparison = agent._create_comparison_table(
            current_loans=sample_loans_2,
            consolidated_amount=200000,
            new_interest_rate=12.5,
            new_tenure=60,
            new_emi=4500,
            current_total_emi=13500,
            current_total_interest=13000,
            new_total_interest=70000
        )
        
        assert "current_loans" in comparison
        assert "consolidated_loan" in comparison
        assert "comparison_metrics" in comparison
        
        # Verify current loans summary
        assert len(comparison["current_loans"]) == 2
        
        # Verify consolidated loan summary
        assert comparison["consolidated_loan"]["amount"] == 200000
        assert comparison["consolidated_loan"]["interest_rate"] == 12.5
        
        # Verify comparison metrics
        metrics = comparison["comparison_metrics"]
        assert metrics["monthly_emi"]["current"] == 13500
        assert metrics["monthly_emi"]["consolidated"] == 4500
        assert metrics["monthly_emi"]["savings"] == 9000
        assert metrics["total_interest"]["savings"] == -57000  # Negative because new is higher
    
    def test_calculate_savings_breakdown(self, agent, sample_loans_2):
        """Test detailed savings breakdown calculation."""
        # First generate an offer
        offer = agent.generate_consolidation_offer(
            active_loans=sample_loans_2,
            credit_score=720,
            customer_id="CUST001"
        )
        
        # Calculate savings breakdown
        savings = agent.calculate_savings_breakdown(offer)
        
        assert "monthly_savings" in savings
        assert "annual_savings" in savings
        assert "total_interest_savings" in savings
        assert "total_emi_savings" in savings
        assert "savings_percentage" in savings
        
        # Verify calculations
        assert savings["annual_savings"] == savings["monthly_savings"] * 12
        # Total EMI savings is calculated over the new tenure
        expected_total_emi_savings = round(savings["monthly_savings"] * offer.new_tenure_months, 2)
        assert savings["total_emi_savings"] == expected_total_emi_savings
        assert 0 <= savings["savings_percentage"] <= 100
    
    def test_offer_id_format(self, agent, sample_loans_2):
        """Test offer ID is generated correctly."""
        offer = agent.generate_consolidation_offer(
            active_loans=sample_loans_2,
            credit_score=720,
            customer_id="CUST001"
        )
        
        assert offer.offer_id.startswith("CONSOL_CUST001_")
        assert len(offer.offer_id) > 20  # Should include timestamp
    
    def test_comparison_table_has_all_loans(self, agent, sample_loans_5):
        """Test comparison table includes all loans being consolidated."""
        offer = agent.generate_consolidation_offer(
            active_loans=sample_loans_5,
            credit_score=750,
            customer_id="CUST003"
        )
        
        current_loans = offer.comparison_table["current_loans"]
        assert len(current_loans) == 5
        
        # Verify all loan IDs are present
        loan_ids = [loan["loan_id"] for loan in current_loans]
        assert "LOAN001" in loan_ids
        assert "LOAN002" in loan_ids
        assert "LOAN003" in loan_ids
        assert "LOAN004" in loan_ids
        assert "LOAN005" in loan_ids
    
    def test_savings_percentage_calculation(self, agent, sample_loans_2):
        """Test savings percentage is calculated correctly."""
        offer = agent.generate_consolidation_offer(
            active_loans=sample_loans_2,
            credit_score=720,
            customer_id="CUST001"
        )
        
        metrics = offer.comparison_table["comparison_metrics"]
        savings_pct = metrics["monthly_emi"]["savings_percentage"]
        
        expected_pct = (offer.monthly_savings / offer.current_total_emi) * 100
        assert abs(savings_pct - expected_pct) < 0.01  # Allow small rounding difference
    
    def test_tenure_selection_logic(self, agent):
        """Test tenure selection uses max of existing or 60 months."""
        # Case 1: Max existing tenure < 60
        loans_short = [
            Loan(
                loan_id="LOAN001",
                loan_type="Personal Loan",
                lender="Bank A",
                principal=100000,
                outstanding=50000,
                interest_rate=14.0,
                monthly_emi=3000,
                remaining_tenure=12
            ),
            Loan(
                loan_id="LOAN002",
                loan_type="Credit Card",
                lender="Bank B",
                principal=50000,
                outstanding=30000,
                interest_rate=18.0,
                monthly_emi=2500,
                remaining_tenure=15
            )
        ]
        
        terms = agent._calculate_consolidated_terms(
            total_outstanding=80000,
            credit_score=720,
            active_loans=loans_short,
            current_avg_rate=15.0
        )
        
        assert terms["tenure_months"] == 60  # Should use 60 as it's greater than 15
        
        # Case 2: Max existing tenure > 60
        loans_long = [
            Loan(
                loan_id="LOAN001",
                loan_type="Personal Loan",
                lender="Bank A",
                principal=200000,
                outstanding=150000,
                interest_rate=14.0,
                monthly_emi=5000,
                remaining_tenure=72
            ),
            Loan(
                loan_id="LOAN002",
                loan_type="Auto Loan",
                lender="Bank B",
                principal=300000,
                outstanding=200000,
                interest_rate=12.0,
                monthly_emi=6000,
                remaining_tenure=48
            )
        ]
        
        terms = agent._calculate_consolidated_terms(
            total_outstanding=350000,
            credit_score=720,
            active_loans=loans_long,
            current_avg_rate=13.0
        )
        
        assert terms["tenure_months"] == 72  # Should use 72 as it's the max



class TestMultipleLoansConsolidationFlow:
    """Test multiple loans consolidation flow for 2-5 loans (Task 14.5)."""
    
    def test_consolidation_with_two_loans(self):
        """Test consolidation with exactly 2 loans."""
        agent = DebtConsolidationAgent()
        
        loans = [
            Loan(loan_id="LOAN001", loan_type="Personal Loan", lender="Bank A",
                 principal=200000, outstanding=150000, interest_rate=14.0,
                 monthly_emi=8000, remaining_tenure=20),
            Loan(loan_id="LOAN002", loan_type="Credit Card", lender="Bank B",
                 principal=50000, outstanding=50000, interest_rate=18.0,
                 monthly_emi=4000, remaining_tenure=15)
        ]
        
        offer = agent.generate_consolidation_offer(
            active_loans=loans,
            credit_score=720,
            customer_id="CUST_2LOANS"
        )
        
        # Verify consolidation
        assert offer.consolidated_amount == 200000  # 150k + 50k
        assert offer.current_total_emi == 12000  # 8k + 4k
        assert offer.new_monthly_emi < 12000  # Should save money on monthly EMI
        assert offer.monthly_savings > 0  # Monthly savings is the key benefit
        # Note: total_interest_savings may be negative if tenure is extended
        # The main benefit is lower monthly EMI for better cash flow
        assert len(offer.loans_being_consolidated) == 2
    
    def test_consolidation_with_three_loans(self):
        """Test consolidation with 3 loans."""
        agent = DebtConsolidationAgent()
        
        loans = [
            Loan(loan_id="LOAN001", loan_type="Personal Loan", lender="Bank A",
                 principal=150000, outstanding=100000, interest_rate=14.0,
                 monthly_emi=6000, remaining_tenure=18),
            Loan(loan_id="LOAN002", loan_type="Credit Card", lender="Bank B",
                 principal=50000, outstanding=40000, interest_rate=18.0,
                 monthly_emi=3000, remaining_tenure=15),
            Loan(loan_id="LOAN003", loan_type="Auto Loan", lender="Bank C",
                 principal=200000, outstanding=120000, interest_rate=12.0,
                 monthly_emi=5000, remaining_tenure=25)
        ]
        
        offer = agent.generate_consolidation_offer(
            active_loans=loans,
            credit_score=700,
            customer_id="CUST_3LOANS"
        )
        
        # Verify consolidation
        assert offer.consolidated_amount == 260000  # 100k + 40k + 120k
        assert offer.current_total_emi == 14000  # 6k + 3k + 5k
        assert offer.new_monthly_emi < 14000
        assert offer.monthly_savings > 0
        assert len(offer.loans_being_consolidated) == 3
    
    def test_consolidation_with_four_loans(self):
        """Test consolidation with 4 loans."""
        agent = DebtConsolidationAgent()
        
        loans = [
            Loan(loan_id=f"LOAN{i:03d}", loan_type="Personal Loan", lender=f"Bank {chr(65+i)}",
                 principal=100000, outstanding=80000, interest_rate=14.0 + i,
                 monthly_emi=5000, remaining_tenure=18)
            for i in range(4)
        ]
        
        offer = agent.generate_consolidation_offer(
            active_loans=loans,
            credit_score=720,
            customer_id="CUST_4LOANS"
        )
        
        # Verify consolidation
        assert offer.consolidated_amount == 320000  # 80k * 4
        assert offer.current_total_emi == 20000  # 5k * 4
        assert offer.new_monthly_emi < 20000
        assert offer.monthly_savings > 0
        assert len(offer.loans_being_consolidated) == 4
    
    def test_consolidation_with_five_loans(self):
        """Test consolidation with exactly 5 loans (maximum)."""
        agent = DebtConsolidationAgent()
        
        loans = [
            Loan(loan_id=f"LOAN{i:03d}", loan_type="Personal Loan", lender=f"Bank {chr(65+i)}",
                 principal=100000, outstanding=70000, interest_rate=14.0 + i * 0.5,
                 monthly_emi=4500, remaining_tenure=16)
            for i in range(5)
        ]
        
        offer = agent.generate_consolidation_offer(
            active_loans=loans,
            credit_score=750,
            customer_id="CUST_5LOANS"
        )
        
        # Verify consolidation
        assert offer.consolidated_amount == 350000  # 70k * 5
        assert offer.current_total_emi == 22500  # 4.5k * 5
        assert offer.new_monthly_emi < 22500
        assert offer.monthly_savings > 0
        assert len(offer.loans_being_consolidated) == 5
    
    def test_savings_highlighting_for_multiple_loans(self):
        """Test that monthly savings are properly calculated and highlighted."""
        agent = DebtConsolidationAgent()
        
        loans = [
            Loan(loan_id="LOAN001", loan_type="Personal Loan", lender="Bank A",
                 principal=200000, outstanding=150000, interest_rate=16.0,
                 monthly_emi=9000, remaining_tenure=18),
            Loan(loan_id="LOAN002", loan_type="Credit Card", lender="Bank B",
                 principal=80000, outstanding=80000, interest_rate=20.0,
                 monthly_emi=6000, remaining_tenure=15),
            Loan(loan_id="LOAN003", loan_type="Personal Loan", lender="Bank C",
                 principal=100000, outstanding=70000, interest_rate=15.0,
                 monthly_emi=4500, remaining_tenure=16)
        ]
        
        offer = agent.generate_consolidation_offer(
            active_loans=loans,
            credit_score=720,
            customer_id="CUST_SAVINGS"
        )
        
        # Verify monthly savings are significant (main benefit of consolidation)
        assert offer.monthly_savings > 1000  # Should save at least ₹1000/month
        
        # Verify savings calculation
        expected_monthly_savings = offer.current_total_emi - offer.new_monthly_emi
        assert abs(offer.monthly_savings - expected_monthly_savings) < 1  # Allow for rounding
        
        # Verify the offer reduces monthly burden
        assert offer.new_monthly_emi < offer.current_total_emi
        
        # Note: total_interest_savings may be negative if tenure is extended
        # The primary benefit is improved monthly cash flow, not necessarily total interest savings
    
    def test_consolidation_rejects_one_loan(self):
        """Test that consolidation rejects single loan."""
        agent = DebtConsolidationAgent()
        
        profile = CreditProfile(
            customer_id="CUST_1LOAN",
            credit_score=720,
            active_loans=[
                Loan(loan_id="LOAN001", loan_type="Personal Loan", lender="Bank A",
                     principal=200000, outstanding=150000, interest_rate=14.0,
                     monthly_emi=8000, remaining_tenure=20)
            ],
            total_outstanding=150000,
            total_monthly_emi=8000,
            debt_to_income_ratio=16.0,
            monthly_income=50000
        )
        
        session_state = {"session_id": "test"}
        input_data = {"credit_profile": profile}
        
        with pytest.raises(BusinessLogicError) as exc_info:
            agent.process(input_data, session_state)
        
        assert "at least 2 loans" in str(exc_info.value).lower()
    
    def test_consolidation_rejects_six_loans(self):
        """Test that consolidation rejects more than 5 loans."""
        agent = DebtConsolidationAgent()
        
        loans = [
            Loan(loan_id=f"LOAN{i:03d}", loan_type="Personal Loan", lender=f"Bank {chr(65+i)}",
                 principal=50000, outstanding=40000, interest_rate=14.0,
                 monthly_emi=2500, remaining_tenure=18)
            for i in range(6)
        ]
        
        profile = CreditProfile(
            customer_id="CUST_6LOANS",
            credit_score=720,
            active_loans=loans,
            total_outstanding=240000,
            total_monthly_emi=15000,
            debt_to_income_ratio=30.0,
            monthly_income=50000
        )
        
        session_state = {"session_id": "test"}
        input_data = {"credit_profile": profile}
        
        with pytest.raises(BusinessLogicError) as exc_info:
            agent.process(input_data, session_state)
        
        assert "cannot consolidate more than 5 loans" in str(exc_info.value).lower()
    
    def test_process_method_with_valid_consolidation(self):
        """Test process method with valid 2-5 loan consolidation."""
        agent = DebtConsolidationAgent()
        
        loans = [
            Loan(loan_id="LOAN001", loan_type="Personal Loan", lender="Bank A",
                 principal=150000, outstanding=120000, interest_rate=15.0,
                 monthly_emi=7000, remaining_tenure=18),
            Loan(loan_id="LOAN002", loan_type="Credit Card", lender="Bank B",
                 principal=60000, outstanding=60000, interest_rate=19.0,
                 monthly_emi=5000, remaining_tenure=14)
        ]
        
        profile = CreditProfile(
            customer_id="CUST_PROCESS",
            credit_score=720,
            active_loans=loans,
            total_outstanding=180000,
            total_monthly_emi=12000,
            debt_to_income_ratio=24.0,
            monthly_income=50000
        )
        
        session_state = {"session_id": "test_session"}
        input_data = {"credit_profile": profile}
        
        response = agent.process(input_data, session_state)
        
        # Verify response
        assert response["success"] is True
        assert response["next_agent"] == "sales"
        assert "save you" in response["message"].lower()
        assert response["data"]["monthly_savings"] > 0
    
    def test_various_loan_count_scenarios(self):
        """Test consolidation with various loan counts from 2 to 5."""
        agent = DebtConsolidationAgent()
        
        for loan_count in [2, 3, 4, 5]:
            loans = [
                Loan(loan_id=f"LOAN{i:03d}", loan_type="Personal Loan", lender=f"Bank {chr(65+i)}",
                     principal=100000, outstanding=75000, interest_rate=14.0 + i * 0.5,
                     monthly_emi=5000, remaining_tenure=16)
                for i in range(loan_count)
            ]
            
            offer = agent.generate_consolidation_offer(
                active_loans=loans,
                credit_score=720,
                customer_id=f"CUST_{loan_count}LOANS"
            )
            
            # Verify offer is generated
            assert offer.consolidated_amount == 75000 * loan_count
            assert offer.current_total_emi == 5000 * loan_count
            assert offer.new_monthly_emi < offer.current_total_emi
            assert offer.monthly_savings > 0
            assert len(offer.loans_being_consolidated) == loan_count
    
    def test_consolidation_comparison_table_includes_all_loans(self):
        """Test that comparison table includes all loans being consolidated."""
        agent = DebtConsolidationAgent()
        
        loans = [
            Loan(loan_id="LOAN001", loan_type="Personal Loan", lender="Bank A",
                 principal=150000, outstanding=100000, interest_rate=14.0,
                 monthly_emi=6000, remaining_tenure=18),
            Loan(loan_id="LOAN002", loan_type="Credit Card", lender="Bank B",
                 principal=50000, outstanding=50000, interest_rate=18.0,
                 monthly_emi=4000, remaining_tenure=14),
            Loan(loan_id="LOAN003", loan_type="Auto Loan", lender="Bank C",
                 principal=200000, outstanding=150000, interest_rate=12.0,
                 monthly_emi=7000, remaining_tenure=22)
        ]
        
        offer = agent.generate_consolidation_offer(
            active_loans=loans,
            credit_score=720,
            customer_id="CUST_TABLE"
        )
        
        # Verify comparison table exists and has data
        assert offer.comparison_table is not None
        assert len(offer.loans_being_consolidated) == 3
        
        # Verify all loans are included
        loan_ids = [loan.loan_id for loan in offer.loans_being_consolidated]
        assert "LOAN001" in loan_ids
        assert "LOAN002" in loan_ids
        assert "LOAN003" in loan_ids
