"""
Unit tests for Credit Bureau Agent

Tests credit profile retrieval, portfolio analysis, DTI calculation,
and flow determination logic for all scenarios.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from agents.credit_bureau_agent import CreditBureauAgent
from agents.base_agent import ValidationError, DataError
from schemas.models import CreditProfile, Loan, PortfolioAnalysis


@pytest.fixture
def mock_credit_data():
    """Create mock credit bureau data."""
    return {
        "credit_profiles": [
            {
                "customer_id": "CUST001",
                "credit_score": 720,
                "active_loans": [
                    {
                        "loan_id": "LOAN001",
                        "loan_type": "Personal Loan",
                        "lender": "HDFC Bank",
                        "principal": 200000,
                        "outstanding": 150000,
                        "interest_rate": 14.5,
                        "monthly_emi": 8500,
                        "remaining_tenure": 18
                    },
                    {
                        "loan_id": "LOAN002",
                        "loan_type": "Credit Card",
                        "lender": "ICICI Bank",
                        "principal": 50000,
                        "outstanding": 50000,
                        "interest_rate": 18.0,
                        "monthly_emi": 5000,
                        "remaining_tenure": 12
                    },
                    {
                        "loan_id": "LOAN003",
                        "loan_type": "Personal Loan",
                        "lender": "Axis Bank",
                        "principal": 100000,
                        "outstanding": 75000,
                        "interest_rate": 15.5,
                        "monthly_emi": 4500,
                        "remaining_tenure": 20
                    }
                ],
                "total_outstanding": 275000,
                "total_monthly_emi": 18000,
                "debt_to_income_ratio": 24.0,
                "monthly_income": 75000
            },
            {
                "customer_id": "CUST002",
                "credit_score": 620,
                "active_loans": [
                    {
                        "loan_id": "LOAN004",
                        "loan_type": "Personal Loan",
                        "lender": "Bank A",
                        "principal": 100000,
                        "outstanding": 90000,
                        "interest_rate": 16.0,
                        "monthly_emi": 5000,
                        "remaining_tenure": 20
                    }
                ],
                "total_outstanding": 90000,
                "total_monthly_emi": 5000,
                "debt_to_income_ratio": 11.1,
                "monthly_income": 45000
            },
            {
                "customer_id": "CUST003",
                "credit_score": 780,
                "active_loans": [],
                "total_outstanding": 0,
                "total_monthly_emi": 0,
                "debt_to_income_ratio": 0.0,
                "monthly_income": 80000
            },
            {
                "customer_id": "CUST004",
                "credit_score": 755,
                "active_loans": [
                    {
                        "loan_id": "LOAN005",
                        "loan_type": "Personal Loan",
                        "lender": "Bank B",
                        "principal": 150000,
                        "outstanding": 120000,
                        "interest_rate": 13.0,
                        "monthly_emi": 6000,
                        "remaining_tenure": 24
                    }
                ],
                "total_outstanding": 120000,
                "total_monthly_emi": 6000,
                "debt_to_income_ratio": 10.0,
                "monthly_income": 60000
            },
            {
                "customer_id": "CUST005",
                "credit_score": 690,
                "active_loans": [
                    {"loan_id": "L1", "loan_type": "Personal", "lender": "B1", "principal": 50000, "outstanding": 40000, "interest_rate": 15.0, "monthly_emi": 2000, "remaining_tenure": 24},
                    {"loan_id": "L2", "loan_type": "Personal", "lender": "B2", "principal": 50000, "outstanding": 40000, "interest_rate": 15.0, "monthly_emi": 2000, "remaining_tenure": 24},
                    {"loan_id": "L3", "loan_type": "Personal", "lender": "B3", "principal": 50000, "outstanding": 40000, "interest_rate": 15.0, "monthly_emi": 2000, "remaining_tenure": 24},
                    {"loan_id": "L4", "loan_type": "Personal", "lender": "B4", "principal": 50000, "outstanding": 40000, "interest_rate": 15.0, "monthly_emi": 2000, "remaining_tenure": 24},
                    {"loan_id": "L5", "loan_type": "Personal", "lender": "B5", "principal": 50000, "outstanding": 40000, "interest_rate": 15.0, "monthly_emi": 2000, "remaining_tenure": 24}
                ],
                "total_outstanding": 200000,
                "total_monthly_emi": 10000,
                "debt_to_income_ratio": 20.0,
                "monthly_income": 50000
            },
            {
                "customer_id": "CUST006",
                "credit_score": 680,
                "active_loans": [
                    {"loan_id": "L1", "loan_type": "Personal", "lender": "B1", "principal": 30000, "outstanding": 25000, "interest_rate": 16.0, "monthly_emi": 1500, "remaining_tenure": 20},
                    {"loan_id": "L2", "loan_type": "Personal", "lender": "B2", "principal": 30000, "outstanding": 25000, "interest_rate": 16.0, "monthly_emi": 1500, "remaining_tenure": 20},
                    {"loan_id": "L3", "loan_type": "Personal", "lender": "B3", "principal": 30000, "outstanding": 25000, "interest_rate": 16.0, "monthly_emi": 1500, "remaining_tenure": 20},
                    {"loan_id": "L4", "loan_type": "Personal", "lender": "B4", "principal": 30000, "outstanding": 25000, "interest_rate": 16.0, "monthly_emi": 1500, "remaining_tenure": 20},
                    {"loan_id": "L5", "loan_type": "Personal", "lender": "B5", "principal": 30000, "outstanding": 25000, "interest_rate": 16.0, "monthly_emi": 1500, "remaining_tenure": 20},
                    {"loan_id": "L6", "loan_type": "Personal", "lender": "B6", "principal": 30000, "outstanding": 25000, "interest_rate": 16.0, "monthly_emi": 1500, "remaining_tenure": 20}
                ],
                "total_outstanding": 150000,
                "total_monthly_emi": 9000,
                "debt_to_income_ratio": 18.0,
                "monthly_income": 50000
            }
        ]
    }


@pytest.fixture
def temp_credit_file(mock_credit_data):
    """Create temporary credit data file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(mock_credit_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink()


@pytest.fixture
def agent(temp_credit_file):
    """Create credit bureau agent with temp data file."""
    return CreditBureauAgent(data_path=temp_credit_file)


class TestCreditBureauAgentInitialization:
    """Test agent initialization."""
    
    def test_initialization_with_custom_path(self, temp_credit_file):
        """Test agent initializes with custom data path."""
        agent = CreditBureauAgent(data_path=temp_credit_file)
        assert agent.agent_name == "credit_bureau_agent"
        assert agent.data_path == Path(temp_credit_file)
    
    def test_initialization_with_default_path(self):
        """Test agent initializes with default data path."""
        agent = CreditBureauAgent()
        assert agent.agent_name == "credit_bureau_agent"
        assert "credit_bureau_data.json" in str(agent.data_path)


class TestInputValidation:
    """Test input validation."""
    
    def test_validate_input_success(self, agent):
        """Test successful input validation."""
        input_data = {"customer_id": "CUST001"}
        assert agent.validate_input(input_data) is True
    
    def test_validate_input_missing_customer_id(self, agent):
        """Test validation fails when customer_id is missing."""
        input_data = {}
        with pytest.raises(ValidationError) as exc_info:
            agent.validate_input(input_data)
        assert "customer_id" in str(exc_info.value)
    
    def test_validate_input_empty_customer_id(self, agent):
        """Test validation fails when customer_id is empty."""
        input_data = {"customer_id": ""}
        with pytest.raises(ValidationError) as exc_info:
            agent.validate_input(input_data)
        assert "non-empty" in str(exc_info.value)
    
    def test_validate_input_invalid_type(self, agent):
        """Test validation fails when input is not a dict."""
        with pytest.raises(ValidationError) as exc_info:
            agent.validate_input("invalid")
        assert "dictionary" in str(exc_info.value)


class TestFetchCreditProfile:
    """Test credit profile retrieval."""
    
    def test_fetch_credit_profile_success(self, agent):
        """Test successful credit profile retrieval."""
        profile = agent.fetch_credit_profile("CUST001")
        
        assert isinstance(profile, CreditProfile)
        assert profile.customer_id == "CUST001"
        assert profile.credit_score == 720
        assert len(profile.active_loans) == 3
        assert profile.total_outstanding == 275000
        assert profile.total_monthly_emi == 18000
    
    def test_fetch_credit_profile_not_found(self, agent):
        """Test error when customer not found."""
        with pytest.raises(DataError) as exc_info:
            agent.fetch_credit_profile("NONEXISTENT")
        assert "not found" in str(exc_info.value)
    
    def test_fetch_credit_profile_no_loans(self, agent):
        """Test fetching profile with no active loans."""
        profile = agent.fetch_credit_profile("CUST003")
        
        assert profile.customer_id == "CUST003"
        assert profile.credit_score == 780
        assert len(profile.active_loans) == 0
        assert profile.total_outstanding == 0
        assert profile.total_monthly_emi == 0
    
    def test_fetch_credit_profile_single_loan(self, agent):
        """Test fetching profile with single loan."""
        profile = agent.fetch_credit_profile("CUST004")
        
        assert profile.customer_id == "CUST004"
        assert len(profile.active_loans) == 1
        assert profile.active_loans[0].loan_id == "LOAN005"


class TestAnalyzeLoanPortfolio:
    """Test loan portfolio analysis."""
    
    def test_analyze_portfolio_multiple_loans(self, agent):
        """Test portfolio analysis with multiple loans."""
        loans = [
            Loan(
                loan_id="L1",
                loan_type="Personal",
                principal=100000,
                outstanding=80000,
                interest_rate=14.0,
                monthly_emi=4000,
                remaining_tenure=24
            ),
            Loan(
                loan_id="L2",
                loan_type="Credit Card",
                principal=50000,
                outstanding=40000,
                interest_rate=18.0,
                monthly_emi=3000,
                remaining_tenure=18
            )
        ]
        
        analysis = agent.analyze_loan_portfolio(loans, monthly_income=60000)
        
        assert analysis.total_loans == 2
        assert analysis.total_outstanding == 120000
        assert analysis.total_monthly_emi == 7000
        assert analysis.debt_to_income_ratio == pytest.approx(11.67, rel=0.01)
        # Weighted average: (80000*14 + 40000*18) / 120000 = 15.33
        assert analysis.average_interest_rate == pytest.approx(15.33, rel=0.01)
    
    def test_analyze_portfolio_no_loans(self, agent):
        """Test portfolio analysis with no loans."""
        analysis = agent.analyze_loan_portfolio([], monthly_income=50000)
        
        assert analysis.total_loans == 0
        assert analysis.total_outstanding == 0
        assert analysis.total_monthly_emi == 0
        assert analysis.average_interest_rate == 0.0
        assert analysis.debt_to_income_ratio == 0.0
    
    def test_analyze_portfolio_without_income(self, agent):
        """Test portfolio analysis without income data."""
        loans = [
            Loan(
                loan_id="L1",
                loan_type="Personal",
                principal=100000,
                outstanding=80000,
                interest_rate=14.0,
                monthly_emi=4000,
                remaining_tenure=24
            )
        ]
        
        analysis = agent.analyze_loan_portfolio(loans)
        
        assert analysis.total_loans == 1
        assert analysis.debt_to_income_ratio is None


class TestCalculateDebtToIncome:
    """Test DTI calculation."""
    
    def test_calculate_dti_normal(self, agent):
        """Test DTI calculation with normal values."""
        loans = [
            Loan(
                loan_id="L1",
                loan_type="Personal",
                principal=100000,
                outstanding=80000,
                interest_rate=14.0,
                monthly_emi=5000,
                remaining_tenure=20
            ),
            Loan(
                loan_id="L2",
                loan_type="Personal",
                principal=50000,
                outstanding=40000,
                interest_rate=15.0,
                monthly_emi=3000,
                remaining_tenure=18
            )
        ]
        
        dti = agent.calculate_debt_to_income(loans, monthly_income=40000)
        # (5000 + 3000) / 40000 * 100 = 20%
        assert dti == 20.0
    
    def test_calculate_dti_high_ratio(self, agent):
        """Test DTI calculation with high ratio."""
        loans = [
            Loan(
                loan_id="L1",
                loan_type="Personal",
                principal=100000,
                outstanding=80000,
                interest_rate=14.0,
                monthly_emi=25000,
                remaining_tenure=20
            )
        ]
        
        dti = agent.calculate_debt_to_income(loans, monthly_income=50000)
        assert dti == 50.0
    
    def test_calculate_dti_zero_income(self, agent):
        """Test DTI calculation fails with zero income."""
        loans = [
            Loan(
                loan_id="L1",
                loan_type="Personal",
                principal=100000,
                outstanding=80000,
                interest_rate=14.0,
                monthly_emi=5000,
                remaining_tenure=20
            )
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            agent.calculate_debt_to_income(loans, monthly_income=0)
        assert "greater than 0" in str(exc_info.value)
    
    def test_calculate_dti_no_loans(self, agent):
        """Test DTI calculation with no loans."""
        dti = agent.calculate_debt_to_income([], monthly_income=50000)
        assert dti == 0.0


class TestDetermineFlow:
    """Test flow determination logic."""
    
    def test_determine_flow_low_credit_score(self, agent):
        """Test flow determination for low credit score (< 650)."""
        profile = CreditProfile(
            customer_id="CUST001",
            credit_score=620,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0
        )
        
        flow = agent.determine_flow(profile)
        assert flow == "credit_improvement"
    
    def test_determine_flow_too_many_loans(self, agent):
        """Test flow determination for > 5 loans."""
        loans = [
            Loan(loan_id=f"L{i}", loan_type="Personal", principal=10000, 
                 outstanding=8000, interest_rate=15.0, monthly_emi=500, remaining_tenure=20)
            for i in range(6)
        ]
        
        profile = CreditProfile(
            customer_id="CUST001",
            credit_score=720,
            active_loans=loans,
            total_outstanding=48000,
            total_monthly_emi=3000
        )
        
        flow = agent.determine_flow(profile)
        assert flow == "rejection"
    
    def test_determine_flow_consolidation_two_loans(self, agent):
        """Test flow determination for 2 loans (consolidation)."""
        loans = [
            Loan(loan_id="L1", loan_type="Personal", principal=100000, 
                 outstanding=80000, interest_rate=14.0, monthly_emi=4000, remaining_tenure=24),
            Loan(loan_id="L2", loan_type="Personal", principal=50000, 
                 outstanding=40000, interest_rate=16.0, monthly_emi=2500, remaining_tenure=20)
        ]
        
        profile = CreditProfile(
            customer_id="CUST001",
            credit_score=720,
            active_loans=loans,
            total_outstanding=120000,
            total_monthly_emi=6500
        )
        
        flow = agent.determine_flow(profile)
        assert flow == "consolidation"
    
    def test_determine_flow_consolidation_five_loans(self, agent):
        """Test flow determination for 5 loans (consolidation)."""
        loans = [
            Loan(loan_id=f"L{i}", loan_type="Personal", principal=50000, 
                 outstanding=40000, interest_rate=15.0, monthly_emi=2000, remaining_tenure=24)
            for i in range(5)
        ]
        
        profile = CreditProfile(
            customer_id="CUST001",
            credit_score=720,
            active_loans=loans,
            total_outstanding=200000,
            total_monthly_emi=10000
        )
        
        flow = agent.determine_flow(profile)
        assert flow == "consolidation"
    
    def test_determine_flow_single_loan(self, agent):
        """Test flow determination for 1 loan (underwriting)."""
        loans = [
            Loan(loan_id="L1", loan_type="Personal", principal=100000, 
                 outstanding=80000, interest_rate=14.0, monthly_emi=4000, remaining_tenure=24)
        ]
        
        profile = CreditProfile(
            customer_id="CUST001",
            credit_score=720,
            active_loans=loans,
            total_outstanding=80000,
            total_monthly_emi=4000
        )
        
        flow = agent.determine_flow(profile)
        assert flow == "underwriting"
    
    def test_determine_flow_no_loans(self, agent):
        """Test flow determination for 0 loans (underwriting)."""
        profile = CreditProfile(
            customer_id="CUST001",
            credit_score=720,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0
        )
        
        flow = agent.determine_flow(profile)
        assert flow == "underwriting"
    
    def test_determine_flow_edge_case_650_score(self, agent):
        """Test flow determination at credit score boundary (650)."""
        profile = CreditProfile(
            customer_id="CUST001",
            credit_score=650,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0
        )
        
        flow = agent.determine_flow(profile)
        # 650 should go to underwriting (not credit improvement)
        assert flow == "underwriting"
    
    def test_determine_flow_edge_case_649_score(self, agent):
        """Test flow determination just below boundary (649)."""
        profile = CreditProfile(
            customer_id="CUST001",
            credit_score=649,
            active_loans=[],
            total_outstanding=0,
            total_monthly_emi=0
        )
        
        flow = agent.determine_flow(profile)
        assert flow == "credit_improvement"


class TestProcessMethod:
    """Test main process method."""
    
    def test_process_success_consolidation_flow(self, agent):
        """Test successful processing for consolidation flow."""
        input_data = {"customer_id": "CUST001"}
        session_state = {}
        
        result = agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert result["agent"] == "credit_bureau_agent"
        assert "data" in result
        assert "credit_profile" in result["data"]
        assert "portfolio_analysis" in result["data"]
        assert result["data"]["recommended_flow"] == "consolidation"
        assert result["next_agent"] == "consolidation"
        assert "consolidate" in result["message"].lower()
    
    def test_process_success_credit_improvement_flow(self, agent):
        """Test successful processing for credit improvement flow."""
        input_data = {"customer_id": "CUST002"}
        session_state = {}
        
        result = agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert result["data"]["recommended_flow"] == "credit_improvement"
        assert result["next_agent"] == "underwriting"
        assert "credit score" in result["message"].lower()
    
    def test_process_success_no_loans_flow(self, agent):
        """Test successful processing for no loans flow."""
        input_data = {"customer_id": "CUST003"}
        session_state = {}
        
        result = agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert result["data"]["recommended_flow"] == "underwriting"
        assert result["next_agent"] == "underwriting"
        assert len(result["data"]["credit_profile"]["active_loans"]) == 0
    
    def test_process_success_single_loan_flow(self, agent):
        """Test successful processing for single loan flow."""
        input_data = {"customer_id": "CUST004"}
        session_state = {}
        
        result = agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert result["data"]["recommended_flow"] == "underwriting"
        assert result["next_agent"] == "underwriting"
        assert len(result["data"]["credit_profile"]["active_loans"]) == 1
    
    def test_process_success_rejection_flow(self, agent):
        """Test successful processing for rejection flow (> 5 loans)."""
        input_data = {"customer_id": "CUST006"}
        session_state = {}
        
        result = agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert result["data"]["recommended_flow"] == "rejection"
        assert result["next_agent"] == "sales"
        assert len(result["data"]["credit_profile"]["active_loans"]) == 6
    
    def test_process_invalid_input(self, agent):
        """Test process with invalid input."""
        input_data = {}
        session_state = {}
        
        with pytest.raises(ValidationError):
            agent.process(input_data, session_state)
    
    def test_process_customer_not_found(self, agent):
        """Test process with non-existent customer."""
        input_data = {"customer_id": "NONEXISTENT"}
        session_state = {}
        
        with pytest.raises(DataError):
            agent.process(input_data, session_state)


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_missing_data_file(self):
        """Test error when data file doesn't exist."""
        agent = CreditBureauAgent(data_path="/nonexistent/path.json")
        
        with pytest.raises(DataError) as exc_info:
            agent.fetch_credit_profile("CUST001")
        assert "not found" in str(exc_info.value)
    
    def test_invalid_json_file(self):
        """Test error when data file contains invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content {")
            temp_path = f.name
        
        try:
            agent = CreditBureauAgent(data_path=temp_path)
            with pytest.raises(DataError) as exc_info:
                agent.fetch_credit_profile("CUST001")
            assert "Invalid JSON" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
