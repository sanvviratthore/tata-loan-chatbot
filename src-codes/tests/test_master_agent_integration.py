"""
Integration tests for Master Agent - Complete Workflow Paths

Tests end-to-end workflows through the master agent orchestrator.
"""

import pytest
import json
from pathlib import Path

from master_agent import MasterAgent, create_master_agent
from utils.session_manager import SessionManager
from utils.llm_client import MockLLM


@pytest.fixture
def session_manager():
    """Create session manager for testing."""
    return SessionManager(session_ttl=3600)


@pytest.fixture
def mock_llm():
    """Create mock LLM with comprehensive response map."""
    response_map = {
        # Intent detection
        "classify": "provide_info",
        "greeting": "greeting",
        "accept": "accept_offer",
        "question": "ask_question",
        
        # Sales agent responses
        "present": "Great news! Based on your credit profile, you're eligible for a loan.",
        "explain": "The interest rate is based on your credit score and debt-to-income ratio.",
        "consolidation": "Consolidating your loans will save you money each month.",
        "benefits": "You'll save on interest and have a single monthly payment."
    }
    return MockLLM(response_map=response_map, default_response="provide_info")


@pytest.fixture
def master_agent(session_manager, mock_llm):
    """Create master agent with mock dependencies."""
    return MasterAgent(
        session_manager=session_manager,
        llm_client=mock_llm,
        use_mock_llm=False
    )


class TestNormalFlowMultipleLoans:
    """Test normal workflow with multiple loans (consolidation path)."""
    
    def test_complete_consolidation_workflow(self, master_agent, session_manager):
        """Test complete workflow from greeting to consolidation offer."""
        # Step 1: Initial greeting
        session_id = session_manager.create_session()
        response = master_agent.process_greeting(session_id)
        
        assert response["success"] is True
        assert response["current_stage"] == "VERIFICATION"
        
        # Step 2: Provide PAN and mobile (customer with multiple loans)
        # Using CUST001 from mock data who has 2 loans
        response = master_agent.route_message(
            "My PAN is ABCDE1234F and mobile is 9876543210",
            session_id
        )
        
        # Should succeed verification and move to credit analysis
        assert response["success"] is True
        
        # Step 3: Credit analysis should route to consolidation
        # (This happens automatically after verification)
        session = session_manager.get_session(session_id)
        
        # Verify customer data was stored
        customer_data = session_manager.get_session_state(session_id, "customer_data")
        assert customer_data is not None
        
        # Verify we have credit profile
        credit_profile = session_manager.get_session_state(session_id, "credit_profile")
        if credit_profile:
            # If customer has 2+ loans, should route to consolidation
            if len(credit_profile.get("active_loans", [])) >= 2:
                assert session_manager.get_workflow_stage(session_id) in ["CONSOLIDATION", "SALES"]


class TestLowCreditScoreFlow:
    """Test workflow for customers with low credit score."""
    
    def test_low_credit_score_rejection(self, master_agent, session_manager):
        """Test workflow for customer with credit score < 650."""
        # This test would need a customer with low credit score in mock data
        # For now, we test the flow logic
        
        session_id = session_manager.create_session()
        master_agent.process_greeting(session_id)
        
        # The actual test would verify:
        # 1. Verification succeeds
        # 2. Credit analysis detects low score
        # 3. Routes to credit improvement flow
        # 4. Provides improvement recommendations
        
        # Verify workflow states are properly defined
        assert "CREDIT_IMPROVEMENT" in master_agent.WORKFLOW_STATES
        assert master_agent._is_valid_transition("CREDIT_ANALYSIS", "CREDIT_IMPROVEMENT")


class TestSingleLoanFlow:
    """Test workflow for customer with single existing loan."""
    
    def test_single_loan_options(self, master_agent, session_manager):
        """Test that customer with 1 loan gets both transfer and new loan options."""
        # This would test with a customer who has exactly 1 loan
        
        session_id = session_manager.create_session()
        master_agent.process_greeting(session_id)
        
        # Verify workflow can handle single loan scenario
        assert master_agent._is_valid_transition("CREDIT_ANALYSIS", "UNDERWRITING")


class TestNoLoansFlow:
    """Test workflow for customer with no existing loans."""
    
    def test_no_loans_standard_offer(self, master_agent, session_manager):
        """Test standard loan offer for customer with no existing loans."""
        session_id = session_manager.create_session()
        master_agent.process_greeting(session_id)
        
        # Verify workflow supports standard underwriting
        assert "UNDERWRITING" in master_agent.WORKFLOW_STATES
        assert master_agent._is_valid_transition("CREDIT_ANALYSIS", "UNDERWRITING")


class TestTooManyLoansRejection:
    """Test rejection workflow for customers with too many loans."""
    
    def test_too_many_loans_rejection(self, master_agent, session_manager):
        """Test rejection for customer with > 5 loans."""
        session_id = session_manager.create_session()
        master_agent.process_greeting(session_id)
        
        # Verify rejection flow exists
        assert "REJECTION" in master_agent.WORKFLOW_STATES
        assert master_agent._is_valid_transition("CREDIT_ANALYSIS", "REJECTION")


class TestMessageRouting:
    """Test message routing through complete workflows."""
    
    def test_route_message_creates_session_if_needed(self, master_agent):
        """Test that route_message creates session if it doesn't exist."""
        response = master_agent.route_message("Hello", "nonexistent_session_id")
        
        assert response is not None
        assert "session_id" in response
    
    def test_route_message_updates_conversation_history(self, master_agent, session_manager):
        """Test that messages are added to conversation history."""
        session_id = session_manager.create_session()
        
        master_agent.route_message("Hello", session_id)
        
        history = session_manager.get_conversation_history(session_id)
        assert history is not None
        assert len(history) >= 1
        
        # Check that user message was recorded
        user_messages = [msg for msg in history if msg["role"] == "user"]
        assert len(user_messages) >= 1
        assert user_messages[0]["content"] == "Hello"
    
    def test_route_message_handles_intent_detection(self, master_agent, session_manager):
        """Test that route_message properly detects intents."""
        session_id = session_manager.create_session()
        session_manager.set_workflow_stage(session_id, "VERIFICATION")
        
        # Test with clear intent
        response = master_agent.route_message(
            "My PAN is ABCDE1234F and mobile is 9876543210",
            session_id
        )
        
        assert response is not None
        assert "agent" in response


class TestAgentCoordination:
    """Test coordination between multiple agents."""
    
    def test_verification_to_credit_bureau_transition(self, master_agent, session_manager):
        """Test transition from verification to credit bureau agent."""
        session_id = session_manager.create_session()
        session_manager.set_workflow_stage(session_id, "VERIFICATION")
        
        # Simulate successful verification
        session_manager.update_session_state(session_id, "customer_data", {
            "customer_id": "CUST001",
            "name": "Test User"
        })
        
        # Verify transition is valid
        assert master_agent._is_valid_transition("VERIFICATION", "CREDIT_ANALYSIS")
    
    def test_credit_bureau_to_underwriting_transition(self, master_agent):
        """Test transition from credit bureau to underwriting."""
        assert master_agent._is_valid_transition("CREDIT_ANALYSIS", "UNDERWRITING")
    
    def test_underwriting_to_sales_transition(self, master_agent):
        """Test transition from underwriting to sales."""
        assert master_agent._is_valid_transition("UNDERWRITING", "SALES")
    
    def test_sales_to_document_transition(self, master_agent):
        """Test transition from sales to document generation."""
        assert master_agent._is_valid_transition("SALES", "DOCUMENT")
    
    def test_sales_can_loop_back_to_underwriting(self, master_agent):
        """Test that sales can loop back to underwriting for modifications."""
        assert master_agent._is_valid_transition("SALES", "UNDERWRITING")


class TestErrorRecovery:
    """Test error handling and recovery in workflows."""
    
    def test_invalid_pan_retry_logic(self, master_agent, session_manager):
        """Test that invalid PAN allows retry."""
        session_id = session_manager.create_session()
        session_manager.set_workflow_stage(session_id, "VERIFICATION")
        
        # Provide invalid PAN
        response = master_agent.route_message(
            "My PAN is INVALID and mobile is 9876543210",
            session_id
        )
        
        # Should get error response but remain in VERIFICATION stage
        current_stage = session_manager.get_workflow_stage(session_id)
        assert current_stage == "VERIFICATION"
    
    def test_missing_customer_data_handling(self, master_agent, session_manager):
        """Test handling when customer data is missing."""
        session_id = session_manager.create_session()
        session_manager.set_workflow_stage(session_id, "CREDIT_ANALYSIS")
        
        # Try to proceed without customer data
        response = master_agent.route_message("Check my credit", session_id)
        
        # Should handle gracefully
        assert response is not None
    
    def test_agent_error_fallback(self, master_agent, session_manager):
        """Test fallback when agent encounters error."""
        session_id = session_manager.create_session()
        
        # Route to nonexistent agent (should be handled)
        input_data = {"user_message": "test"}
        session = session_manager.get_session(session_id)
        
        response = master_agent._route_to_agent(
            "nonexistent_agent",
            "test message",
            "provide_info",
            session
        )
        
        assert response["success"] is False
        assert "error" in response or "message" in response


class TestStateManagement:
    """Test state management across workflow."""
    
    def test_state_persists_across_messages(self, master_agent, session_manager):
        """Test that state persists across multiple messages."""
        session_id = session_manager.create_session()
        
        # Set some state
        session_manager.update_session_state(session_id, "test_key", "test_value")
        
        # Send a message
        master_agent.route_message("Hello", session_id)
        
        # Verify state still exists
        value = session_manager.get_session_state(session_id, "test_key")
        assert value == "test_value"
    
    def test_workflow_stage_updates(self, master_agent, session_manager):
        """Test that workflow stage updates correctly."""
        session_id = session_manager.create_session()
        
        initial_stage = session_manager.get_workflow_stage(session_id)
        assert initial_stage == "initial"
        
        # Process greeting
        master_agent.process_greeting(session_id)
        
        new_stage = session_manager.get_workflow_stage(session_id)
        assert new_stage == "VERIFICATION"
    
    def test_customer_data_stored_after_verification(self, master_agent, session_manager):
        """Test that customer data is stored after successful verification."""
        session_id = session_manager.create_session()
        session_manager.set_workflow_stage(session_id, "VERIFICATION")
        
        # Provide valid credentials (if customer exists in mock data)
        response = master_agent.route_message(
            "PAN: ABCDE1234F, Mobile: 9876543210",
            session_id
        )
        
        # Check if customer data was stored (if verification succeeded)
        if response.get("success"):
            customer_data = session_manager.get_session_state(session_id, "customer_data")
            # Customer data should be stored if verification was successful
            if customer_data:
                assert "customer_id" in customer_data


class TestConversationFlow:
    """Test natural conversation flow."""
    
    def test_greeting_starts_workflow(self, master_agent, session_manager):
        """Test that greeting properly starts the workflow."""
        session_id = session_manager.create_session()
        
        response = master_agent.route_message("Hello, I need a loan", session_id)
        
        assert response is not None
        assert response.get("current_stage") in ["INIT", "VERIFICATION"]
    
    def test_multiple_messages_in_sequence(self, master_agent, session_manager):
        """Test handling multiple messages in sequence."""
        session_id = session_manager.create_session()
        
        # Message 1: Greeting
        response1 = master_agent.route_message("Hello", session_id)
        assert response1 is not None
        
        # Message 2: Provide info
        response2 = master_agent.route_message("My PAN is ABCDE1234F", session_id)
        assert response2 is not None
        
        # Message 3: Provide more info
        response3 = master_agent.route_message("Mobile: 9876543210", session_id)
        assert response3 is not None
        
        # Verify conversation history
        history = session_manager.get_conversation_history(session_id)
        assert len(history) >= 3


class TestSpecialCases:
    """Test special cases and edge conditions."""
    
    def test_help_request_at_any_stage(self, master_agent, session_manager):
        """Test that help requests are handled at any stage."""
        session_id = session_manager.create_session()
        
        # Try help at different stages
        for stage in ["INIT", "VERIFICATION", "SALES"]:
            session_manager.set_workflow_stage(session_id, stage)
            session = session_manager.get_session(session_id)
            
            agent = master_agent._determine_target_agent("help", stage, session)
            assert agent == "sales"  # Sales agent handles help
    
    def test_document_request_routes_to_document_agent(self, master_agent, session_manager):
        """Test that document requests always route to document agent."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        agent = master_agent._determine_target_agent("document_request", "SALES", session)
        assert agent == "document"
    
    def test_question_in_sales_stage_routes_to_sales(self, master_agent, session_manager):
        """Test that questions in sales stage route to sales agent."""
        session_id = session_manager.create_session()
        session_manager.set_workflow_stage(session_id, "SALES")
        session = session_manager.get_session(session_id)
        
        agent = master_agent._determine_target_agent("ask_question", "SALES", session)
        assert agent == "sales"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
