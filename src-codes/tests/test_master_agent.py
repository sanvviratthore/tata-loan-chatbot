"""
Integration tests for Master Agent Orchestrator

Tests all workflow paths and agent routing logic.
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
    """Create mock LLM with predefined responses."""
    response_map = {
        "greeting": "greeting",
        "hello": "greeting",
        "loan": "greeting",
        "provide": "provide_info",
        "pan": "provide_info",
        "mobile": "provide_info",
        "accept": "accept_offer",
        "yes": "accept_offer",
        "reject": "reject_offer",
        "no": "reject_offer",
        "modify": "modify_request",
        "change": "modify_request",
        "question": "ask_question",
        "what": "ask_question",
        "how": "ask_question",
        "document": "document_request",
        "pdf": "document_request",
        "help": "help"
    }
    return MockLLM(response_map=response_map, default_response="provide_info")


@pytest.fixture
def master_agent(session_manager, mock_llm):
    """Create master agent with mock dependencies."""
    return MasterAgent(
        session_manager=session_manager,
        llm_client=mock_llm,
        use_mock_llm=False  # We're providing our own mock
    )


class TestMasterAgentInitialization:
    """Test master agent initialization."""
    
    def test_initialization(self, master_agent):
        """Test that master agent initializes correctly."""
        assert master_agent is not None
        assert master_agent.session_manager is not None
        assert master_agent.llm is not None
        assert len(master_agent.agents) == 6
        assert "verification" in master_agent.agents
        assert "credit_bureau" in master_agent.agents
        assert "underwriting" in master_agent.agents
        assert "consolidation" in master_agent.agents
        assert "sales" in master_agent.agents
        assert "document" in master_agent.agents
    
    def test_workflow_states_defined(self, master_agent):
        """Test that workflow states are properly defined."""
        assert "INIT" in master_agent.WORKFLOW_STATES
        assert "VERIFICATION" in master_agent.WORKFLOW_STATES
        assert "CREDIT_ANALYSIS" in master_agent.WORKFLOW_STATES
        assert "UNDERWRITING" in master_agent.WORKFLOW_STATES
        assert "CONSOLIDATION" in master_agent.WORKFLOW_STATES
        assert "SALES" in master_agent.WORKFLOW_STATES
        assert "DOCUMENT" in master_agent.WORKFLOW_STATES
        assert "END" in master_agent.WORKFLOW_STATES
    
    def test_state_to_agent_mapping(self, master_agent):
        """Test that state to agent mapping is correct."""
        assert master_agent.STATE_TO_AGENT["VERIFICATION"] == "verification"
        assert master_agent.STATE_TO_AGENT["CREDIT_ANALYSIS"] == "credit_bureau"
        assert master_agent.STATE_TO_AGENT["UNDERWRITING"] == "underwriting"
        assert master_agent.STATE_TO_AGENT["CONSOLIDATION"] == "consolidation"
        assert master_agent.STATE_TO_AGENT["SALES"] == "sales"
        assert master_agent.STATE_TO_AGENT["DOCUMENT"] == "document"


class TestIntentDetection:
    """Test intent detection functionality."""
    
    def test_detect_greeting_intent(self, master_agent, session_manager):
        """Test detection of greeting intent."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        intent = master_agent.detect_intent("Hello, I need a loan", "INIT", session)
        assert intent == "greeting"
        
        intent = master_agent.detect_intent("Hi there", "INIT", session)
        assert intent == "greeting"
    
    def test_detect_accept_intent(self, master_agent, session_manager):
        """Test detection of accept offer intent."""
        session_id = session_manager.create_session()
        session_manager.set_workflow_stage(session_id, "SALES")
        session = session_manager.get_session(session_id)
        
        intent = master_agent.detect_intent("Yes, I accept", "SALES", session)
        assert intent == "accept_offer"
        
        intent = master_agent.detect_intent("Sounds good, proceed", "SALES", session)
        assert intent == "accept_offer"
    
    def test_detect_reject_intent(self, master_agent, session_manager):
        """Test detection of reject offer intent."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        intent = master_agent.detect_intent("No, I'm not interested", "SALES", session)
        assert intent == "reject_offer"
    
    def test_detect_modify_intent(self, master_agent, session_manager):
        """Test detection of modify request intent."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        intent = master_agent.detect_intent("Can I change the tenure?", "SALES", session)
        assert intent == "modify_request"
        
        intent = master_agent.detect_intent("I want to increase the amount", "SALES", session)
        assert intent == "modify_request"
    
    def test_detect_question_intent(self, master_agent, session_manager):
        """Test detection of question intent."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        intent = master_agent.detect_intent("What is the interest rate?", "SALES", session)
        assert intent == "ask_question"
        
        intent = master_agent.detect_intent("How does this work?", "SALES", session)
        assert intent == "ask_question"
    
    def test_detect_document_request_intent(self, master_agent, session_manager):
        """Test detection of document request intent."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        intent = master_agent.detect_intent("Can I get the offer letter?", "SALES", session)
        assert intent == "document_request"
        
        intent = master_agent.detect_intent("Download PDF", "SALES", session)
        assert intent == "document_request"


class TestAgentRouting:
    """Test agent routing logic."""
    
    def test_determine_agent_for_init_stage(self, master_agent, session_manager):
        """Test agent determination for INIT stage."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        agent = master_agent._determine_target_agent("greeting", "INIT", session)
        assert agent == "verification"
    
    def test_determine_agent_for_verification_stage(self, master_agent, session_manager):
        """Test agent determination for VERIFICATION stage."""
        session_id = session_manager.create_session()
        session_manager.set_workflow_stage(session_id, "VERIFICATION")
        session = session_manager.get_session(session_id)
        
        agent = master_agent._determine_target_agent("provide_info", "VERIFICATION", session)
        assert agent == "verification"
    
    def test_determine_agent_for_credit_analysis_stage(self, master_agent, session_manager):
        """Test agent determination for CREDIT_ANALYSIS stage."""
        session_id = session_manager.create_session()
        session_manager.set_workflow_stage(session_id, "CREDIT_ANALYSIS")
        session = session_manager.get_session(session_id)
        
        agent = master_agent._determine_target_agent("provide_info", "CREDIT_ANALYSIS", session)
        assert agent == "credit_bureau"
    
    def test_determine_agent_for_document_request(self, master_agent, session_manager):
        """Test that document requests route to document agent."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        agent = master_agent._determine_target_agent("document_request", "SALES", session)
        assert agent == "document"
    
    def test_determine_agent_for_help_request(self, master_agent, session_manager):
        """Test that help requests route to sales agent."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        agent = master_agent._determine_target_agent("help", "VERIFICATION", session)
        assert agent == "sales"


class TestWorkflowTransitions:
    """Test workflow state transitions."""
    
    def test_valid_transition_from_init(self, master_agent):
        """Test valid transitions from INIT state."""
        assert master_agent._is_valid_transition("INIT", "VERIFICATION") is True
        assert master_agent._is_valid_transition("INIT", "CREDIT_ANALYSIS") is False
    
    def test_valid_transition_from_verification(self, master_agent):
        """Test valid transitions from VERIFICATION state."""
        assert master_agent._is_valid_transition("VERIFICATION", "CREDIT_ANALYSIS") is True
        assert master_agent._is_valid_transition("VERIFICATION", "UNDERWRITING") is False
    
    def test_valid_transition_from_credit_analysis(self, master_agent):
        """Test valid transitions from CREDIT_ANALYSIS state."""
        assert master_agent._is_valid_transition("CREDIT_ANALYSIS", "UNDERWRITING") is True
        assert master_agent._is_valid_transition("CREDIT_ANALYSIS", "CONSOLIDATION") is True
        assert master_agent._is_valid_transition("CREDIT_ANALYSIS", "CREDIT_IMPROVEMENT") is True
        assert master_agent._is_valid_transition("CREDIT_ANALYSIS", "REJECTION") is True
        assert master_agent._is_valid_transition("CREDIT_ANALYSIS", "DOCUMENT") is False
    
    def test_valid_transition_from_sales(self, master_agent):
        """Test valid transitions from SALES state."""
        assert master_agent._is_valid_transition("SALES", "DOCUMENT") is True
        assert master_agent._is_valid_transition("SALES", "UNDERWRITING") is True
        assert master_agent._is_valid_transition("SALES", "VERIFICATION") is False
    
    def test_agent_to_stage_conversion(self, master_agent):
        """Test conversion from agent name to stage."""
        assert master_agent._agent_to_stage("verification") == "VERIFICATION"
        assert master_agent._agent_to_stage("credit_bureau") == "CREDIT_ANALYSIS"
        assert master_agent._agent_to_stage("underwriting") == "UNDERWRITING"
        assert master_agent._agent_to_stage("consolidation") == "CONSOLIDATION"
        assert master_agent._agent_to_stage("sales") == "SALES"
        assert master_agent._agent_to_stage("document") == "DOCUMENT"


class TestInputPreparation:
    """Test input data preparation for agents."""
    
    def test_prepare_verification_input(self, master_agent, session_manager):
        """Test input preparation for verification agent."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        message = "My PAN is ABCDE1234F and mobile is 9876543210"
        input_data = master_agent._prepare_agent_input(
            "verification", message, "provide_info", session
        )
        
        assert "pan" in input_data
        assert input_data["pan"] == "ABCDE1234F"
        assert "mobile" in input_data
        assert input_data["mobile"] == "9876543210"
    
    def test_prepare_credit_bureau_input(self, master_agent, session_manager):
        """Test input preparation for credit bureau agent."""
        session_id = session_manager.create_session()
        session_manager.update_session_state(session_id, "customer_data", {
            "customer_id": "CUST001",
            "name": "Test User"
        })
        session = session_manager.get_session(session_id)
        
        input_data = master_agent._prepare_agent_input(
            "credit_bureau", "Check my credit", "provide_info", session
        )
        
        assert "customer_id" in input_data
        assert input_data["customer_id"] == "CUST001"
    
    def test_prepare_underwriting_input_with_amount(self, master_agent, session_manager):
        """Test input preparation for underwriting with loan amount."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        message = "I need a loan of 5 lakh"
        input_data = master_agent._prepare_agent_input(
            "underwriting", message, "provide_info", session
        )
        
        assert "requested_amount" in input_data
        assert input_data["requested_amount"] == 500000  # 5 lakh = 500000


class TestErrorHandling:
    """Test error handling and fallbacks."""
    
    def test_handle_validation_error(self, master_agent):
        """Test handling of validation errors."""
        from agents.base_agent import ValidationError
        
        error = ValidationError("Invalid input")
        response = master_agent.handle_error(error)
        
        assert response["success"] is False
        assert response["error_type"] == "VALIDATION_ERROR"
        assert response["recoverable"] is True
        assert "additional information" in response["message"].lower()
    
    def test_handle_agent_error(self, master_agent):
        """Test handling of agent errors."""
        from agents.base_agent import AgentError
        
        error = AgentError("Agent failed", error_type="TEST_ERROR", recoverable=True)
        response = master_agent.handle_error(error)
        
        assert response["success"] is False
        assert response["error_type"] == "TEST_ERROR"
        assert response["recoverable"] is True
    
    def test_handle_unknown_error(self, master_agent):
        """Test handling of unknown errors."""
        error = Exception("Unknown error")
        response = master_agent.handle_error(error)
        
        assert response["success"] is False
        assert response["error_type"] == "SYSTEM_ERROR"
        assert response["recoverable"] is True
        assert "unexpected issue" in response["message"].lower()


class TestSessionManagement:
    """Test session management functionality."""
    
    def test_reset_session(self, master_agent, session_manager):
        """Test session reset functionality."""
        session_id = session_manager.create_session()
        session_manager.update_session_state(session_id, "test_key", "test_value")
        
        result = master_agent.reset_session(session_id)
        assert result is True
    
    def test_get_conversation_summary(self, master_agent, session_manager):
        """Test conversation summary retrieval."""
        session_id = session_manager.create_session()
        session_manager.add_conversation_message(session_id, "user", "Hello")
        session_manager.add_conversation_message(session_id, "assistant", "Hi there")
        
        summary = master_agent.get_conversation_summary(session_id)
        
        assert summary is not None
        assert summary["session_id"] == session_id
        assert summary["message_count"] == 2
        assert "current_stage" in summary
    
    def test_get_conversation_summary_nonexistent_session(self, master_agent):
        """Test conversation summary for nonexistent session."""
        summary = master_agent.get_conversation_summary("nonexistent_id")
        assert summary is None
    
    def test_process_greeting(self, master_agent, session_manager):
        """Test greeting processing."""
        session_id = session_manager.create_session()
        
        response = master_agent.process_greeting(session_id)
        
        assert response["success"] is True
        assert "welcome" in response["message"].lower()
        assert response["current_stage"] == "VERIFICATION"
        assert "pan" in response["message"].lower()
        assert "mobile" in response["message"].lower()


class TestGetNextAgent:
    """Test next agent determination."""
    
    def test_get_next_agent_from_verification(self, master_agent):
        """Test next agent after verification."""
        agent_output = {"next_agent": "credit_bureau"}
        next_agent = master_agent.get_next_agent("verification", agent_output)
        assert next_agent == "credit_bureau"
    
    def test_get_next_agent_from_underwriting(self, master_agent):
        """Test next agent after underwriting."""
        agent_output = {"next_agent": "sales"}
        next_agent = master_agent.get_next_agent("underwriting", agent_output)
        assert next_agent == "sales"
    
    def test_get_next_agent_default_progression(self, master_agent):
        """Test default workflow progression."""
        next_agent = master_agent.get_next_agent("verification", {})
        assert next_agent == "credit_bureau"
        
        next_agent = master_agent.get_next_agent("underwriting", {})
        assert next_agent == "sales"
        
        next_agent = master_agent.get_next_agent("sales", {})
        assert next_agent == "document"
    
    def test_get_next_agent_end_of_workflow(self, master_agent):
        """Test next agent at end of workflow."""
        next_agent = master_agent.get_next_agent("document", {})
        assert next_agent is None


class TestFactoryFunction:
    """Test factory function for creating master agent."""
    
    def test_create_master_agent_with_defaults(self):
        """Test creating master agent with default parameters (using mock LLM for testing)."""
        agent = create_master_agent(use_mock_llm=True)
        
        assert agent is not None
        assert agent.session_manager is not None
        assert agent.llm is not None
    
    def test_create_master_agent_with_custom_session_manager(self):
        """Test creating master agent with custom session manager."""
        custom_sm = SessionManager(session_ttl=7200)
        agent = create_master_agent(session_manager=custom_sm, use_mock_llm=True)
        
        assert agent.session_manager is custom_sm
    
    def test_create_master_agent_with_mock_llm(self):
        """Test creating master agent with mock LLM."""
        agent = create_master_agent(use_mock_llm=True)
        
        assert agent is not None
        assert isinstance(agent.llm, MockLLM)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
