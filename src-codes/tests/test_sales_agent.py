"""
Unit tests for Sales Agent.
"""

import pytest
from unittest.mock import Mock, patch
from agents.sales_agent import SalesAgent
from agents.base_agent import ValidationError, BusinessLogicError
from utils.llm_client import MockLLM


@pytest.fixture
def mock_llm():
    """Create mock LLM with predefined responses."""
    response_map = {
        "loan offer": "Great news! We're pleased to offer you a loan of ₹300,000 at 10.5% interest for 60 months. Your monthly EMI will be ₹6,420. Do you have any questions?",
        "consolidation offer": "Excellent news! We can consolidate your loans into one at 12.5% interest. You'll save ₹4,000 every month! Would you like to proceed?",
        "emi": "Your monthly EMI will be ₹6,420. This amount will be automatically debited from your account.",
        "interest": "The interest rate is 10.5% per annum, which is competitive based on your credit profile.",
        "modification": "I've adjusted your offer to ₹300,000 over 72 months. Your new EMI is ₹5,500. Does this work better?",
        "add-on": "We also offer Loan Protection Insurance and a Premium Credit Card that might interest you. Would you like to know more?"
    }
    return MockLLM(response_map=response_map)


@pytest.fixture
def sales_agent(mock_llm):
    """Create sales agent with mock LLM."""
    return SalesAgent(llm_client=mock_llm)


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
        "total_repayment": 385200
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
        "loans_being_consolidated": []
    }


@pytest.fixture
def sample_session_state(sample_loan_offer):
    """Sample session state."""
    return {
        "session_id": "sess_123",
        "user_id": "CUST001",
        "current_agent": "sales",
        "workflow_stage": "SALES",
        "customer_data": {
            "customer_id": "CUST001",
            "name": "Rajesh Kumar",
            "credit_score": 750,
            "monthly_income": 75000
        },
        "current_offer": sample_loan_offer,
        "conversation_history": []
    }


class TestSalesAgentInitialization:
    """Test sales agent initialization."""
    
    def test_initialization_with_mock_llm(self, mock_llm):
        """Test agent initializes with mock LLM."""
        agent = SalesAgent(llm_client=mock_llm)
        assert agent.agent_name == "sales_agent"
        assert agent.llm_client == mock_llm
        assert len(agent.addon_products) == 3
    
    def test_initialization_without_llm(self):
        """Test agent initializes with default LLM."""
        with patch('agents.sales_agent.create_llm_client') as mock_create:
            mock_create.return_value = Mock()
            agent = SalesAgent()
            assert agent.llm_client is not None
            mock_create.assert_called_once()


class TestInputValidation:
    """Test input validation."""
    
    def test_validate_valid_input(self, sales_agent):
        """Test validation passes for valid input."""
        input_data = {"action": "present_offer", "offer": {}}
        assert sales_agent.validate_input(input_data) is True
    
    def test_validate_missing_action(self, sales_agent):
        """Test validation fails when action is missing."""
        with pytest.raises(ValidationError) as exc_info:
            sales_agent.validate_input({})
        assert "action" in str(exc_info.value)
    
    def test_validate_invalid_action(self, sales_agent):
        """Test validation fails for invalid action."""
        with pytest.raises(ValidationError) as exc_info:
            sales_agent.validate_input({"action": "invalid_action"})
        assert "Invalid action" in str(exc_info.value)
    
    def test_validate_non_dict_input(self, sales_agent):
        """Test validation fails for non-dictionary input."""
        with pytest.raises(ValidationError) as exc_info:
            sales_agent.validate_input("not a dict")
        assert "dictionary" in str(exc_info.value)


class TestPresentOffer:
    """Test offer presentation functionality."""
    
    def test_present_loan_offer(self, sales_agent, sample_loan_offer, sample_session_state):
        """Test presenting a loan offer."""
        input_data = {
            "action": "present_offer",
            "offer": sample_loan_offer,
            "offer_type": "loan"
        }
        
        result = sales_agent.process(input_data, sample_session_state)
        
        assert result["success"] is True
        assert "presentation" in result["data"]
        assert "offer" in result["data"]
        assert result["data"]["offer_type"] == "loan"
        assert "300,000" in result["data"]["presentation"] or "loan" in result["data"]["presentation"].lower()
    
    def test_present_consolidation_offer(self, sales_agent, sample_consolidation_offer, sample_session_state):
        """Test presenting a consolidation offer."""
        input_data = {
            "action": "present_offer",
            "offer": sample_consolidation_offer,
            "offer_type": "consolidation"
        }
        
        result = sales_agent.process(input_data, sample_session_state)
        
        assert result["success"] is True
        assert "presentation" in result["data"]
        assert result["data"]["offer_type"] == "consolidation"
    
    def test_present_offer_missing_data(self, sales_agent, sample_session_state):
        """Test presenting offer fails without offer data."""
        input_data = {
            "action": "present_offer",
            "offer_type": "loan"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            sales_agent.process(input_data, sample_session_state)
        assert "offer data" in str(exc_info.value).lower()
    
    def test_present_offer_with_llm_failure(self, sample_loan_offer, sample_session_state):
        """Test fallback presentation when LLM fails."""
        failing_llm = Mock()
        failing_llm.generate.side_effect = Exception("LLM error")
        
        agent = SalesAgent(llm_client=failing_llm)
        
        presentation = agent.present_offer(sample_loan_offer, "loan", sample_session_state)
        
        assert "300,000" in presentation
        assert "10.5%" in presentation
        assert "approved" in presentation.lower()


class TestAnswerQuestion:
    """Test question answering functionality."""
    
    def test_answer_question_about_emi(self, sales_agent, sample_session_state):
        """Test answering question about EMI."""
        input_data = {
            "action": "answer_question",
            "question": "What is my monthly EMI?"
        }
        
        result = sales_agent.process(input_data, sample_session_state)
        
        assert result["success"] is True
        assert "answer" in result["data"]
        assert "question" in result["data"]
    
    def test_answer_question_about_interest(self, sales_agent, sample_session_state):
        """Test answering question about interest rate."""
        input_data = {
            "action": "answer_question",
            "question": "What is the interest rate?"
        }
        
        result = sales_agent.process(input_data, sample_session_state)
        
        assert result["success"] is True
        assert "answer" in result["data"]
    
    def test_answer_question_missing_question(self, sales_agent, sample_session_state):
        """Test answering fails without question."""
        input_data = {"action": "answer_question"}
        
        with pytest.raises(ValidationError) as exc_info:
            sales_agent.process(input_data, sample_session_state)
        assert "question" in str(exc_info.value).lower()
    
    def test_answer_question_no_active_offer(self, sales_agent):
        """Test answering fails without active offer."""
        input_data = {
            "action": "answer_question",
            "question": "What is my EMI?"
        }
        session_state = {"session_id": "sess_123"}
        
        with pytest.raises(BusinessLogicError) as exc_info:
            sales_agent.process(input_data, session_state)
        assert "no active offer" in str(exc_info.value).lower()
    
    def test_answer_question_with_llm_failure(self, sample_loan_offer, sample_session_state):
        """Test fallback answer when LLM fails."""
        failing_llm = Mock()
        failing_llm.generate.side_effect = Exception("LLM error")
        
        agent = SalesAgent(llm_client=failing_llm)
        
        answer = agent.answer_question("What is my EMI?", sample_loan_offer, sample_session_state)
        
        assert "6,420" in answer or "6420" in answer
        assert "emi" in answer.lower()


class TestModifyOffer:
    """Test offer modification functionality."""
    
    def test_modify_increase_tenure(self, sales_agent, sample_session_state):
        """Test increasing loan tenure."""
        input_data = {
            "action": "modify_offer",
            "modification": "increase tenure by 12 months"
        }
        
        result = sales_agent.process(input_data, sample_session_state)
        
        assert result["success"] is True
        assert "modified_offer" in result["data"]
        assert result["data"]["modified_offer"]["tenure_months"] == 72  # 60 + 12
        assert result["data"]["modified_offer"]["monthly_emi"] < sample_session_state["current_offer"]["monthly_emi"]
    
    def test_modify_decrease_tenure(self, sales_agent, sample_session_state):
        """Test decreasing loan tenure."""
        input_data = {
            "action": "modify_offer",
            "modification": "reduce tenure to 48 months"
        }
        
        result = sales_agent.process(input_data, sample_session_state)
        
        assert result["success"] is True
        assert result["data"]["modified_offer"]["tenure_months"] == 48
        assert result["data"]["modified_offer"]["monthly_emi"] > sample_session_state["current_offer"]["monthly_emi"]
    
    def test_modify_increase_amount(self, sales_agent, sample_session_state):
        """Test increasing loan amount."""
        input_data = {
            "action": "modify_offer",
            "modification": "increase loan amount"
        }
        
        result = sales_agent.process(input_data, sample_session_state)
        
        assert result["success"] is True
        assert result["data"]["modified_offer"]["loan_amount"] > sample_session_state["current_offer"]["loan_amount"]
    
    def test_modify_decrease_amount(self, sales_agent, sample_session_state):
        """Test decreasing loan amount."""
        input_data = {
            "action": "modify_offer",
            "modification": "reduce loan amount"
        }
        
        result = sales_agent.process(input_data, sample_session_state)
        
        assert result["success"] is True
        assert result["data"]["modified_offer"]["loan_amount"] < sample_session_state["current_offer"]["loan_amount"]
    
    def test_modify_consolidation_offer(self, sales_agent, sample_consolidation_offer):
        """Test modifying consolidation offer."""
        session_state = {
            "session_id": "sess_123",
            "current_offer": sample_consolidation_offer
        }
        
        input_data = {
            "action": "modify_offer",
            "modification": "extend tenure"
        }
        
        result = sales_agent.process(input_data, session_state)
        
        assert result["success"] is True
        assert "new_tenure_months" in result["data"]["modified_offer"]
        assert result["data"]["modified_offer"]["new_tenure_months"] > sample_consolidation_offer["new_tenure_months"]
    
    def test_modify_no_active_offer(self, sales_agent):
        """Test modification fails without active offer."""
        input_data = {
            "action": "modify_offer",
            "modification": "increase tenure"
        }
        session_state = {"session_id": "sess_123"}
        
        with pytest.raises(BusinessLogicError) as exc_info:
            sales_agent.process(input_data, session_state)
        assert "no active offer" in str(exc_info.value).lower()
    
    def test_modify_missing_modification(self, sales_agent, sample_session_state):
        """Test modification fails without modification request."""
        input_data = {"action": "modify_offer"}
        
        with pytest.raises(ValidationError) as exc_info:
            sales_agent.process(input_data, sample_session_state)
        assert "modification" in str(exc_info.value).lower()


class TestSuggestAddons:
    """Test add-on product suggestions."""
    
    def test_suggest_addons_basic(self, sales_agent, sample_session_state):
        """Test suggesting add-on products."""
        input_data = {"action": "suggest_addons"}
        
        result = sales_agent.process(input_data, sample_session_state)
        
        assert result["success"] is True
        assert "suggestions" in result["data"]
        assert len(result["data"]["suggestions"]) > 0
        assert "presentation" in result["data"]
    
    def test_suggest_addons_high_credit_score(self, sales_agent):
        """Test add-ons for high credit score customer."""
        session_state = {
            "session_id": "sess_123",
            "customer_data": {"credit_score": 780, "monthly_income": 100000},
            "current_offer": {"loan_amount": 500000}
        }
        
        suggestions = sales_agent.upsell_products(session_state["customer_data"], session_state["current_offer"])
        
        # Should include credit card for high credit score
        product_names = [s["name"] for s in suggestions]
        assert "Premium Credit Card" in product_names
        assert "Loan Protection Insurance" in product_names
    
    def test_suggest_addons_low_credit_score(self, sales_agent):
        """Test add-ons for low credit score customer."""
        session_state = {
            "session_id": "sess_123",
            "customer_data": {"credit_score": 650, "monthly_income": 50000},
            "current_offer": {"loan_amount": 100000}
        }
        
        suggestions = sales_agent.upsell_products(session_state["customer_data"], session_state["current_offer"])
        
        # Should not include credit card for low credit score
        product_names = [s["name"] for s in suggestions]
        assert "Premium Credit Card" not in product_names
        assert "Loan Protection Insurance" in product_names
    
    def test_suggest_addons_high_loan_amount(self, sales_agent):
        """Test add-ons for high loan amount."""
        session_state = {
            "session_id": "sess_123",
            "customer_data": {"credit_score": 750, "monthly_income": 100000},
            "current_offer": {"loan_amount": 500000}
        }
        
        suggestions = sales_agent.upsell_products(session_state["customer_data"], session_state["current_offer"])
        
        # Should include overdraft for high loan amount
        product_names = [s["name"] for s in suggestions]
        assert "Overdraft Facility" in product_names
        
        # Check overdraft limit
        overdraft = next(s for s in suggestions if s["name"] == "Overdraft Facility")
        assert overdraft["limit"] == 100000  # 20% of 500000
    
    def test_insurance_cost_calculation(self, sales_agent):
        """Test insurance cost is calculated correctly."""
        offer = {"loan_amount": 200000}
        suggestions = sales_agent.upsell_products({}, offer)
        
        insurance = next(s for s in suggestions if s["name"] == "Loan Protection Insurance")
        assert insurance["cost"] == 1000  # 0.5% of 200000


class TestAcceptOffer:
    """Test offer acceptance functionality."""
    
    def test_accept_offer_success(self, sales_agent, sample_session_state):
        """Test accepting an offer."""
        input_data = {"action": "accept_offer"}
        
        result = sales_agent.process(input_data, sample_session_state)
        
        assert result["success"] is True
        assert "accepted_offer" in result["data"]
        assert result["data"]["accepted_offer"] == sample_session_state["current_offer"]
        assert result["next_agent"] == "document"
        assert "confirmation" in result["data"]
    
    def test_accept_offer_no_active_offer(self, sales_agent):
        """Test accepting fails without active offer."""
        input_data = {"action": "accept_offer"}
        session_state = {"session_id": "sess_123"}
        
        with pytest.raises(BusinessLogicError) as exc_info:
            sales_agent.process(input_data, session_state)
        assert "no active offer" in str(exc_info.value).lower()
    
    def test_accept_offer_confirmation_message(self, sales_agent, sample_loan_offer):
        """Test acceptance confirmation message."""
        confirmation = sales_agent._generate_acceptance_confirmation(sample_loan_offer)
        
        assert "300,000" in confirmation
        assert "documents" in confirmation.lower()
        assert "offer letter" in confirmation.lower()


class TestAddonProducts:
    """Test add-on product catalog."""
    
    def test_addon_products_structure(self, sales_agent):
        """Test add-on products have required fields."""
        for product_id, product in sales_agent.addon_products.items():
            assert "name" in product
            assert "description" in product
            assert "benefits" in product
            assert isinstance(product["benefits"], list)
    
    def test_loan_protection_insurance_details(self, sales_agent):
        """Test loan protection insurance details."""
        insurance = sales_agent.addon_products["loan_protection_insurance"]
        assert insurance["name"] == "Loan Protection Insurance"
        assert insurance["cost_percentage"] == 0.5
        assert len(insurance["benefits"]) >= 3
    
    def test_credit_card_details(self, sales_agent):
        """Test credit card details."""
        card = sales_agent.addon_products["credit_card"]
        assert card["name"] == "Premium Credit Card"
        assert "annual_fee" in card
        assert card["annual_fee"] > 0
    
    def test_overdraft_details(self, sales_agent):
        """Test overdraft facility details."""
        overdraft = sales_agent.addon_products["overdraft_facility"]
        assert overdraft["name"] == "Overdraft Facility"
        assert "interest_rate" in overdraft
        assert overdraft["interest_rate"] > 0


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_process_unknown_action(self, sales_agent, sample_session_state):
        """Test processing unknown action."""
        input_data = {"action": "unknown_action"}
        
        with pytest.raises(ValidationError):
            sales_agent.process(input_data, sample_session_state)
    
    def test_modify_with_extreme_values(self, sales_agent, sample_session_state):
        """Test modification handles extreme values."""
        # Test maximum tenure limit
        input_data = {
            "action": "modify_offer",
            "modification": "increase tenure to 200 months"
        }
        
        result = sales_agent.process(input_data, sample_session_state)
        
        # Should cap at 84 months
        assert result["data"]["modified_offer"]["tenure_months"] <= 84
    
    def test_empty_session_state(self, sales_agent):
        """Test handling empty session state."""
        input_data = {"action": "answer_question", "question": "What is my EMI?"}
        
        with pytest.raises(BusinessLogicError):
            sales_agent.process(input_data, {})
    
    def test_llm_client_none(self):
        """Test agent handles None LLM client gracefully."""
        with patch('agents.sales_agent.create_llm_client') as mock_create:
            mock_create.return_value = Mock()
            agent = SalesAgent(llm_client=None)
            # Should create default client
            assert agent.llm_client is not None


class TestLLMIntegration:
    """Test LLM integration and fallbacks."""
    
    def test_llm_called_for_presentation(self, mock_llm, sample_loan_offer, sample_session_state):
        """Test LLM is called for offer presentation."""
        agent = SalesAgent(llm_client=mock_llm)
        
        agent.present_offer(sample_loan_offer, "loan", sample_session_state)
        
        assert mock_llm.call_count > 0
    
    def test_llm_called_for_questions(self, mock_llm, sample_loan_offer, sample_session_state):
        """Test LLM is called for answering questions."""
        agent = SalesAgent(llm_client=mock_llm)
        
        agent.answer_question("What is my EMI?", sample_loan_offer, sample_session_state)
        
        assert mock_llm.call_count > 0
    
    def test_fallback_when_llm_fails(self, sample_loan_offer, sample_session_state):
        """Test fallback responses when LLM fails."""
        failing_llm = Mock()
        failing_llm.generate.side_effect = Exception("API error")
        
        agent = SalesAgent(llm_client=failing_llm)
        
        # Should not raise exception, should use fallback
        presentation = agent.present_offer(sample_loan_offer, "loan", sample_session_state)
        assert len(presentation) > 0
        assert "300,000" in presentation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



cl



class TestSingleLoanComparison:
    """Test single loan comparison presentation (Task 14.2)."""
    
    def test_present_single_loan_comparison_basic(self, mock_llm):
        """Test basic single loan comparison presentation."""
        agent = SalesAgent(llm_client=mock_llm)
        
        comparison = {
            "existing_loan": {
                "loan_id": "LOAN001",
                "loan_type": "Personal Loan",
                "outstanding": 150000,
                "interest_rate": 14.0,
                "monthly_emi": 8000,
                "remaining_tenure": 20
            },
            "option_1_transfer": {
                "description": "Transfer existing loan + new amount",
                "total_amount": 250000,
                "approved": True,
                "interest_rate": 12.5,
                "monthly_emi": 12000,
                "tenure_months": 60,
                "total_monthly_payment": 12000
            },
            "option_2_new_loan": {
                "description": "New loan (keep existing loan separate)",
                "new_loan_amount": 100000,
                "approved": True,
                "interest_rate": 12.5,
                "new_loan_emi": 5500,
                "tenure_months": 60,
                "total_monthly_payment": 13500
            },
            "recommendation": "transfer",
            "recommendation_reason": "Lower monthly payment: ₹12,000 vs ₹13,500",
            "monthly_savings": 1500
        }
        
        presentation = agent.present_single_loan_comparison(comparison, "Rajesh")
        
        # Should return a string
        assert isinstance(presentation, str)
        assert len(presentation) > 0
        
        # Should mention key amounts
        assert "150,000" in presentation or "1,50,000" in presentation
        assert "250,000" in presentation or "2,50,000" in presentation
    
    def test_single_loan_comparison_with_transfer_recommendation(self, mock_llm):
        """Test comparison when transfer is recommended."""
        agent = SalesAgent(llm_client=mock_llm)
        
        comparison = {
            "existing_loan": {
                "loan_id": "LOAN001",
                "loan_type": "Car Loan",
                "outstanding": 200000,
                "interest_rate": 15.0,
                "monthly_emi": 10000,
                "remaining_tenure": 24
            },
            "option_1_transfer": {
                "total_amount": 300000,
                "approved": True,
                "interest_rate": 12.0,
                "monthly_emi": 14000,
                "tenure_months": 60
            },
            "option_2_new_loan": {
                "new_loan_amount": 100000,
                "approved": True,
                "interest_rate": 12.5,
                "new_loan_emi": 5500,
                "total_monthly_payment": 15500
            },
            "recommendation": "transfer",
            "recommendation_reason": "Lower monthly payment and single loan",
            "monthly_savings": 1500
        }
        
        presentation = agent.present_single_loan_comparison(comparison)
        
        assert len(presentation) > 0
        # LLM should be called
        assert mock_llm.call_count > 0
    
    def test_single_loan_comparison_with_new_loan_recommendation(self, mock_llm):
        """Test comparison when new loan is recommended."""
        agent = SalesAgent(llm_client=mock_llm)
        
        comparison = {
            "existing_loan": {
                "loan_id": "LOAN001",
                "loan_type": "Personal Loan",
                "outstanding": 100000,
                "interest_rate": 12.0,
                "monthly_emi": 5000,
                "remaining_tenure": 22
            },
            "option_1_transfer": {
                "total_amount": 200000,
                "approved": True,
                "interest_rate": 12.5,
                "monthly_emi": 10500,
                "tenure_months": 60
            },
            "option_2_new_loan": {
                "new_loan_amount": 100000,
                "approved": True,
                "interest_rate": 12.0,
                "new_loan_emi": 5200,
                "total_monthly_payment": 10200
            },
            "recommendation": "new_loan",
            "recommendation_reason": "Keep loans separate for flexibility",
            "monthly_savings": 0
        }
        
        presentation = agent.present_single_loan_comparison(comparison, "Priya")
        
        assert len(presentation) > 0
        assert "Priya" in presentation or "valued customer" in presentation
    
    def test_single_loan_comparison_fallback(self):
        """Test fallback presentation when LLM fails."""
        failing_llm = Mock()
        failing_llm.generate.side_effect = Exception("LLM API error")
        
        agent = SalesAgent(llm_client=failing_llm)
        
        comparison = {
            "existing_loan": {
                "loan_id": "LOAN001",
                "loan_type": "Personal Loan",
                "outstanding": 150000,
                "interest_rate": 14.0,
                "monthly_emi": 8000,
                "remaining_tenure": 20
            },
            "option_1_transfer": {
                "total_amount": 250000,
                "approved": True,
                "interest_rate": 12.5,
                "monthly_emi": 12000,
                "tenure_months": 60
            },
            "option_2_new_loan": {
                "new_loan_amount": 100000,
                "approved": True,
                "interest_rate": 12.5,
                "new_loan_emi": 5500,
                "total_monthly_payment": 13500
            },
            "recommendation": "transfer",
            "recommendation_reason": "Lower monthly payment",
            "monthly_savings": 1500
        }
        
        # Should not raise exception
        presentation = agent.present_single_loan_comparison(comparison, "Amit")
        
        assert len(presentation) > 0
        assert "Amit" in presentation
        assert "Option 1" in presentation
        assert "Option 2" in presentation
        assert "150,000" in presentation or "1,50,000" in presentation
    
    def test_single_loan_comparison_includes_both_options(self):
        """Test that presentation includes both options clearly."""
        mock_llm = MockLLM(response_map={
            "loan": "Here are your options for the loan."
        })
        
        agent = SalesAgent(llm_client=mock_llm)
        
        comparison = {
            "existing_loan": {
                "loan_id": "LOAN001",
                "loan_type": "Home Loan",
                "outstanding": 500000,
                "interest_rate": 10.0,
                "monthly_emi": 20000,
                "remaining_tenure": 30
            },
            "option_1_transfer": {
                "total_amount": 600000,
                "approved": True,
                "interest_rate": 10.5,
                "monthly_emi": 24000,
                "tenure_months": 60
            },
            "option_2_new_loan": {
                "new_loan_amount": 100000,
                "approved": True,
                "interest_rate": 11.0,
                "new_loan_emi": 5500,
                "total_monthly_payment": 25500
            },
            "recommendation": "transfer",
            "recommendation_reason": "Lower total payment",
            "monthly_savings": 1500
        }
        
        presentation = agent.present_single_loan_comparison(comparison)
        
        # Verify LLM was called with proper context
        assert mock_llm.call_count > 0
        last_prompt = mock_llm.get_last_prompt()
        
        # Prompt should include key information
        assert "500,000" in last_prompt or "5,00,000" in last_prompt
        assert "600,000" in last_prompt or "6,00,000" in last_prompt
        assert "Option 1" in last_prompt
        assert "Option 2" in last_prompt
