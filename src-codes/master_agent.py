"""
Master Agent Orchestrator

Central orchestrator that routes conversations between specialized agents based on
intent detection and workflow state. Manages the complete loan application journey.
"""

import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from agents.base_agent import BaseAgent, AgentError, ValidationError, SystemError, handle_errors
from agents.verification_agent import VerificationAgent
from agents.credit_bureau_agent import CreditBureauAgent
from agents.underwriting_agent import UnderwritingAgent
from agents.debt_consolidation_agent import DebtConsolidationAgent
from agents.sales_agent import SalesAgent
from agents.document_agent import DocumentAgent
from utils.llm_client import BaseLLM, create_llm_client
from utils.session_manager import SessionManager
from utils.logger import get_logger


class MasterAgent:
    """
    Master orchestrator that manages workflow and routes between specialized agents.
    
    Responsibilities:
    - Intent detection from user messages
    - Workflow state management
    - Agent routing based on state and intent
    - Error handling with graceful fallbacks
    - Session coordination
    """
    
    # Workflow state machine - defines valid transitions
    WORKFLOW_STATES = {
        "INIT": ["VERIFICATION"],
        "VERIFICATION": ["CREDIT_ANALYSIS"],
        "CREDIT_ANALYSIS": ["UNDERWRITING", "CONSOLIDATION", "CREDIT_IMPROVEMENT", "REJECTION"],
        "CONSOLIDATION": ["SALES"],
        "UNDERWRITING": ["SALES", "SALARY_VERIFICATION"],
        "SALARY_VERIFICATION": ["UNDERWRITING"],
        "SALES": ["DOCUMENT", "UNDERWRITING"],  # Can loop back for modifications
        "CREDIT_IMPROVEMENT": ["DOCUMENT"],
        "REJECTION": ["END"],
        "DOCUMENT": ["END"],
        "END": []
    }
    
    # Map workflow states to agent names
    STATE_TO_AGENT = {
        "INIT": "master",
        "VERIFICATION": "verification",
        "CREDIT_ANALYSIS": "credit_bureau",
        "CONSOLIDATION": "consolidation",
        "UNDERWRITING": "underwriting",
        "SALARY_VERIFICATION": "verification",
        "SALES": "sales",
        "CREDIT_IMPROVEMENT": "underwriting",
        "REJECTION": "sales",
        "DOCUMENT": "document",
        "END": "master"
    }
    
    def __init__(
        self,
        session_manager: SessionManager,
        llm_client: Optional[BaseLLM] = None,
        use_mock_llm: bool = False
    ):
        """
        Initialize master agent.
        
        Args:
            session_manager: Session manager instance
            llm_client: LLM client for intent detection (optional)
            use_mock_llm: Whether to use mock LLM for testing
        """
        self.logger = get_logger("master_agent")
        self.session_manager = session_manager
        
        # Initialize LLM client
        if llm_client is None:
            self.llm = create_llm_client(use_mock=use_mock_llm)
        else:
            self.llm = llm_client
        
        # Initialize specialized agents (pass LLM client to agents that need it)
        self.agents = {
            "verification": VerificationAgent(),
            "credit_bureau": CreditBureauAgent(),
            "underwriting": UnderwritingAgent(llm_client=self.llm),
            "consolidation": DebtConsolidationAgent(),
            "sales": SalesAgent(llm_client=self.llm),
            "document": DocumentAgent()
        }
        
        self.logger.info("Master agent initialized with all specialized agents")
    
    def route_message(
        self,
        user_message: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Route user message to appropriate agent based on intent and state.
        
        Args:
            user_message: User's input message
            session_id: Session identifier
        
        Returns:
            Dictionary containing agent response and updated state
        """
        try:
            # Get or create session
            session = self.session_manager.get_session(session_id)
            if session is None:
                session_id = self.session_manager.create_session()
                session = self.session_manager.get_session(session_id)
            
            # Log incoming message
            self.session_manager.add_conversation_message(
                session_id=session_id,
                role="user",
                content=user_message
            )
            
            # Get current workflow stage and normalize
            current_stage = self.session_manager.get_workflow_stage(session_id) or "INIT"
            
            # Normalize stage name (handle both "initial" and "INIT")
            if current_stage.lower() == "initial":
                current_stage = "INIT"
                # Update the session with normalized stage
                self.session_manager.set_workflow_stage(session_id, "INIT")
            
            self.logger.info(f"Routing message in stage: {current_stage}")
            
            # Detect intent
            intent = self.detect_intent(user_message, current_stage, session)
            
            self.logger.info(f"Detected intent: {intent}")
            
            # Determine which agent should handle this
            target_agent = self._determine_target_agent(intent, current_stage, session)
            
            self.logger.info(f"Routing to agent: {target_agent}")
            
            # Pre-transition stage if needed (e.g., INIT -> VERIFICATION when routing to verification agent)
            if current_stage == "INIT" and target_agent == "verification":
                self.session_manager.set_workflow_stage(session_id, "VERIFICATION")
                current_stage = "VERIFICATION"
                self.logger.info("Pre-transitioned from INIT to VERIFICATION")
            
            # Route to agent
            agent_response = self._route_to_agent(
                agent_name=target_agent,
                user_message=user_message,
                intent=intent,
                session=session
            )
            
            # Update session with agent response
            if agent_response.get("success"):
                # Store agent data in session first
                if "data" in agent_response:
                    # Special handling for offers (consolidation, underwriting)
                    if target_agent in ["consolidation", "underwriting"]:
                        # Store the entire offer as current_offer
                        self.session_manager.update_session_state(session_id, "current_offer", agent_response["data"])
                    
                    # Also store individual keys
                    for key, value in agent_response["data"].items():
                        self.session_manager.update_session_state(session_id, key, value)
                
                # Update workflow stage if agent suggests next stage
                if "next_agent" in agent_response:
                    next_stage = self._agent_to_stage(agent_response["next_agent"])
                    if self._is_valid_transition(current_stage, next_stage):
                        self.session_manager.set_workflow_stage(session_id, next_stage)
                        self.logger.info(f"Transitioned from {current_stage} to {next_stage}")
                        
                        # Auto-trigger next agent if it doesn't require user input
                        next_agent_name = agent_response["next_agent"]
                        if self._should_auto_trigger(next_agent_name, session):
                            self.logger.info(f"Auto-triggering {next_agent_name} agent")
                            
                            # Get updated session after state changes
                            updated_session = self.session_manager.get_session(session_id)
                            
                            # Call next agent automatically
                            auto_response = self._route_to_agent(
                                agent_name=next_agent_name,
                                user_message="",  # No user message for auto-trigger
                                intent="auto_trigger",
                                session=updated_session
                            )
                            
                            # Append auto-triggered response to the original response
                            if auto_response.get("success"):
                                # Add auto-triggered message to conversation
                                if "message" in auto_response:
                                    self.session_manager.add_conversation_message(
                                        session_id=session_id,
                                        role="assistant",
                                        content=auto_response["message"],
                                        agent=next_agent_name
                                    )
                                
                                # Update agent_response to include auto-triggered data
                                agent_response["message"] = agent_response.get("message", "") + "\n\n" + auto_response.get("message", "")
                                
                                # Store auto-triggered data
                                if "data" in auto_response:
                                    # Special handling for offers (consolidation, underwriting)
                                    if next_agent_name in ["consolidation", "underwriting"]:
                                        # Store the entire offer as current_offer
                                        self.session_manager.update_session_state(session_id, "current_offer", auto_response["data"])
                                    
                                    # Also store individual keys
                                    for key, value in auto_response["data"].items():
                                        self.session_manager.update_session_state(session_id, key, value)
                                
                                # Handle next agent from auto-triggered response
                                if "next_agent" in auto_response:
                                    next_next_stage = self._agent_to_stage(auto_response["next_agent"])
                                    if self._is_valid_transition(next_stage, next_next_stage):
                                        self.session_manager.set_workflow_stage(session_id, next_next_stage)
                                        self.logger.info(f"Auto-transitioned from {next_stage} to {next_next_stage}")
            
            # Add agent response to conversation history
            if "message" in agent_response:
                self.session_manager.add_conversation_message(
                    session_id=session_id,
                    role="assistant",
                    content=agent_response["message"],
                    agent=target_agent
                )
            
            # Return response with session info
            return {
                "success": agent_response.get("success", True),
                "message": agent_response.get("message", ""),
                "data": agent_response.get("data", {}),
                "session_id": session_id,
                "current_stage": self.session_manager.get_workflow_stage(session_id),
                "agent": target_agent
            }
        
        except Exception as e:
            self.logger.error(f"Error in route_message: {str(e)}", exc_info=True)
            return self.handle_error(e, {"session_id": session_id, "user_message": user_message})

    def detect_intent(
        self,
        message: str,
        current_stage: str,
        session: Dict[str, Any]
    ) -> str:
        """
        Detect user intent from message using LLM and context.
        
        Possible intents:
        - greeting: Initial greeting or hello
        - provide_info: User providing requested information
        - ask_question: User asking a question about offer/process
        - accept_offer: User accepting a loan offer
        - reject_offer: User rejecting an offer
        - modify_request: User requesting modifications to offer
        - document_request: User requesting documents
        - help: User asking for help
        
        Args:
            message: User's message
            current_stage: Current workflow stage
            session: Session data
        
        Returns:
            Intent string
        """
        # Rule-based intent detection for common patterns
        message_lower = message.lower().strip()
        
        # Greeting patterns - broader detection for INIT stage
        if current_stage == "INIT":
            if any(word in message_lower for word in ["hello", "hi", "hey", "start", "loan", "need", "looking", "want", "apply", "application"]):
                return "greeting"
        
        # Acceptance patterns
        if any(phrase in message_lower for phrase in ["yes", "accept", "agree", "proceed", "ok", "sure", "sounds good"]):
            if current_stage in ["SALES", "CONSOLIDATION"]:
                return "accept_offer"
            return "provide_info"
        
        # Rejection patterns
        if any(phrase in message_lower for phrase in ["no", "reject", "decline", "not interested", "cancel"]):
            return "reject_offer"
        
        # Modification patterns
        if any(phrase in message_lower for phrase in ["change", "modify", "adjust", "different", "lower", "higher", "increase", "decrease"]):
            return "modify_request"
        
        # Document request patterns
        if any(phrase in message_lower for phrase in ["document", "pdf", "download", "letter", "offer letter", "agreement"]):
            return "document_request"
        
        # Question patterns
        if any(char in message for char in ["?", "what", "how", "why", "when", "where", "explain"]):
            return "ask_question"
        
        # Help patterns
        if any(word in message_lower for word in ["help", "support", "assist", "confused"]):
            return "help"
        
        # Use LLM for complex intent detection
        try:
            prompt = f"""Classify the user's intent from the following message in the context of a loan application process.

Current stage: {current_stage}
User message: "{message}"

Possible intents:
- greeting: Initial greeting or starting conversation
- provide_info: Providing requested information (PAN, mobile, salary, etc.)
- ask_question: Asking a question about the loan, offer, or process
- accept_offer: Accepting a loan offer
- reject_offer: Rejecting an offer
- modify_request: Requesting changes to loan parameters
- document_request: Requesting documents or offer letter
- help: Asking for help or clarification

Return ONLY the intent name, nothing else."""
            
            llm_intent = self.llm.generate(prompt, temperature=0.3, max_tokens=50).strip().lower()
            
            # Validate LLM response
            valid_intents = [
                "greeting", "provide_info", "ask_question", "accept_offer",
                "reject_offer", "modify_request", "document_request", "help"
            ]
            
            if llm_intent in valid_intents:
                return llm_intent
        
        except Exception as e:
            self.logger.warning(f"LLM intent detection failed: {str(e)}")
        
        # Default to provide_info if uncertain
        return "provide_info"
    
    def _determine_target_agent(
        self,
        intent: str,
        current_stage: str,
        session: Dict[str, Any]
    ) -> str:
        """
        Determine which agent should handle the request.
        
        Args:
            intent: Detected user intent
            current_stage: Current workflow stage
            session: Session data
        
        Returns:
            Agent name to route to
        """
        # Handle special intents that can occur at any stage
        if intent == "help":
            return "sales"  # Sales agent handles help requests
        
        if intent == "document_request":
            return "document"
        
        # Route based on current stage
        if current_stage == "INIT":
            # In INIT stage, if it's a greeting, handle at master level
            # Otherwise route to verification for info collection
            if intent == "greeting":
                return "master"
            else:
                # When routing to verification from INIT, we should be in VERIFICATION stage
                # This will be handled by the stage transition logic
                return "verification"
        
        # Get agent for current stage
        agent = self.STATE_TO_AGENT.get(current_stage, "master")
        
        # Special handling for certain intents
        if intent == "modify_request" and current_stage == "SALES":
            # Sales agent handles modifications, may route back to underwriting
            return "sales"
        
        if intent == "ask_question":
            # Sales agent handles questions in most stages
            if current_stage in ["SALES", "CONSOLIDATION", "UNDERWRITING"]:
                return "sales"
        
        return agent
    
    def _route_to_agent(
        self,
        agent_name: str,
        user_message: str,
        intent: str,
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Route request to specific agent.
        
        Args:
            agent_name: Name of agent to route to
            user_message: User's message
            intent: Detected intent
            session: Session data
        
        Returns:
            Agent response dictionary
        """
        try:
            # Handle master agent (initial greeting, general queries)
            if agent_name == "master":
                return self._handle_master_response(user_message, intent, session)
            
            # Get agent instance
            agent = self.agents.get(agent_name)
            
            if agent is None:
                self.logger.error(f"Agent not found: {agent_name}")
                return {
                    "success": False,
                    "message": "I'm having trouble processing your request. Please try again.",
                    "error": f"Agent not found: {agent_name}"
                }
            
            # Prepare input data based on current stage and intent
            input_data = self._prepare_agent_input(
                agent_name=agent_name,
                user_message=user_message,
                intent=intent,
                session=session
            )
            
            # Call agent's process method
            response = agent.process(input_data, session)
            
            return response
        
        except AgentError as e:
            self.logger.error(f"Agent error in {agent_name}: {str(e)}")
            return agent.handle_error(e, {"intent": intent})
        
        except Exception as e:
            self.logger.error(f"Unexpected error routing to {agent_name}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "I encountered an unexpected error. Please try again.",
                "error": str(e)
            }
    
    def _handle_master_response(
        self,
        user_message: str,
        intent: str,
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle requests that should be handled by master agent directly.
        
        Args:
            user_message: User's message
            intent: Detected intent
            session: Session data
        
        Returns:
            Response dictionary
        """
        # Handle greeting - this sets up the verification stage
        if intent == "greeting":
            message = """Hello! Welcome to Tata Loan Services. I'm here to help you with your personal loan needs.

To get started, I'll need to verify your identity. Please provide:
1. Your PAN card number (format: ABCDE1234F)
2. Your registered mobile number

You can provide both details in your next message."""
            
            # Return with next_agent to trigger stage transition
            return {
                "success": True,
                "message": message,
                "next_agent": "verification",
                "data": {
                    "awaiting_verification": True
                }
            }
        
        # Handle general queries
        elif intent == "help":
            message = """I can help you with:
- Applying for a new personal loan
- Consolidating multiple existing loans
- Understanding your loan eligibility
- Answering questions about loan terms and conditions
- Generating loan offer documents

What would you like to do today?"""
            
            return {
                "success": True,
                "message": message
            }
        
        # Default response
        else:
            message = """I'm here to assist you with your loan needs. To get started, please let me know:
- Are you looking for a new loan?
- Do you want to consolidate existing loans?
- Do you have questions about our services?"""
            
            return {
                "success": True,
                "message": message
            }
    
    def _prepare_agent_input(
        self,
        agent_name: str,
        user_message: str,
        intent: str,
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare input data for agent based on context.
        
        Args:
            agent_name: Target agent name
            user_message: User's message
            intent: Detected intent
            session: Session data
        
        Returns:
            Input data dictionary for agent
        """
        input_data = {
            "user_message": user_message,
            "intent": intent
        }
        
        # Add context based on agent type
        if agent_name == "verification":
            # Extract PAN and mobile from message if present
            pan_match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', user_message.upper())
            mobile_match = re.search(r'\b[6-9][0-9]{9}\b', user_message)
            
            if pan_match:
                input_data["pan"] = pan_match.group()
            if mobile_match:
                input_data["mobile"] = mobile_match.group()
        
        elif agent_name == "credit_bureau":
            # Need customer_id from session
            customer_data = session.get("state", {}).get("customer_data")
            if customer_data:
                input_data["customer_id"] = customer_data.get("customer_id")
        
        elif agent_name == "underwriting":
            # Need credit profile from session
            credit_profile = session.get("state", {}).get("credit_profile")
            if credit_profile:
                input_data["credit_profile"] = credit_profile
            
            # Check if requesting specific loan amount
            amount_match = re.search(r'₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:lakh|lac|thousand|k)?', user_message.lower())
            if amount_match:
                amount_str = amount_match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    # Convert lakhs/thousands if mentioned
                    if 'lakh' in user_message.lower() or 'lac' in user_message.lower():
                        amount *= 100000
                    elif 'thousand' in user_message.lower() or 'k' in user_message.lower():
                        amount *= 1000
                    input_data["requested_amount"] = amount
                except ValueError:
                    pass
        
        elif agent_name == "consolidation":
            # Need credit profile with active loans
            credit_profile = session.get("state", {}).get("credit_profile")
            if credit_profile:
                input_data["credit_profile"] = credit_profile
        
        elif agent_name == "sales":
            # Map intent to sales agent action
            intent_to_action = {
                "ask_question": "answer_question",
                "accept_offer": "accept_offer",
                "reject_offer": "answer_question",  # Handle rejection as a question/conversation
                "modify_request": "modify_offer",
                "provide_info": "present_offer",
                "help": "answer_question"
            }
            
            # Set action based on intent
            action = intent_to_action.get(intent, "answer_question")
            input_data["action"] = action
            
            # Need current offer from session
            # Check multiple possible keys for the offer
            current_offer = session.get("state", {}).get("current_offer")
            
            # Debug logging
            self.logger.info(f"Sales agent preparation - current_offer found: {current_offer is not None}")
            if current_offer:
                self.logger.info(f"Offer type: {current_offer.get('offer_id', 'unknown')}")
            
            if not current_offer:
                # Try consolidation offer data stored with individual keys
                state = session.get("state", {})
                if "offer_id" in state:
                    # Reconstruct the offer from individual keys
                    current_offer = {
                        k: v for k, v in state.items() 
                        if k in ["offer_id", "customer_id", "consolidated_amount", "new_interest_rate", 
                                "new_tenure_months", "new_monthly_emi", "current_total_emi", 
                                "monthly_savings", "total_interest_savings", "loans_being_consolidated",
                                "comparison_table"]
                    }
                    self.logger.info(f"Reconstructed offer from state keys: {list(current_offer.keys())}")
            
            if current_offer:
                input_data["offer"] = current_offer
            else:
                self.logger.warning("No offer found in session for sales agent")
            
            # Add customer data for context
            customer_data = session.get("state", {}).get("customer_data")
            if customer_data:
                input_data["customer_data"] = customer_data
            
            # Add credit profile for context
            credit_profile = session.get("state", {}).get("credit_profile")
            if credit_profile:
                input_data["credit_profile"] = credit_profile
        
        elif agent_name == "document":
            # Determine document type based on offer type
            current_offer = session.get("state", {}).get("current_offer")
            customer_data = session.get("state", {}).get("customer_data")
            
            # Determine document type from offer
            if current_offer:
                # Check if it's a consolidation offer or regular loan offer
                if "consolidated_amount" in current_offer or "CONSOL" in current_offer.get("offer_id", ""):
                    input_data["document_type"] = "consolidation_report"
                    input_data["consolidation_offer"] = current_offer
                    input_data["customer"] = customer_data
                else:
                    input_data["document_type"] = "loan_offer"
                    input_data["offer"] = current_offer
                    input_data["customer"] = customer_data
            else:
                # Default to loan offer
                input_data["document_type"] = "loan_offer"
                if current_offer:
                    input_data["offer"] = current_offer
                if customer_data:
                    input_data["customer"] = customer_data
            
            if customer_data:
                input_data["customer_data"] = customer_data
        
        return input_data

    def _should_auto_trigger(self, agent_name: str, session: Dict[str, Any]) -> bool:
        """
        Determine if an agent should be automatically triggered without user input.
        
        Some agents like credit_bureau don't need user input - they just need
        data from the session state.
        
        Args:
            agent_name: Name of the agent
            session: Current session state
        
        Returns:
            True if agent should be auto-triggered
        """
        # Credit bureau agent should auto-trigger after verification
        if agent_name == "credit_bureau":
            # Check if we have customer_data in session
            customer_data = session.get("state", {}).get("customer_data")
            return customer_data is not None
        
        # Add other auto-trigger agents here if needed
        # For example, document agent might auto-trigger after offer acceptance
        
        return False
    
    def _is_valid_transition(self, from_stage: str, to_stage: str) -> bool:
        """
        Check if transition between workflow stages is valid.
        
        Args:
            from_stage: Current stage
            to_stage: Target stage
        
        Returns:
            True if transition is valid
        """
        valid_next_stages = self.WORKFLOW_STATES.get(from_stage, [])
        is_valid = to_stage in valid_next_stages
        
        if not is_valid:
            self.logger.warning(
                f"Invalid workflow transition attempted: {from_stage} -> {to_stage}"
            )
        
        return is_valid
    
    def _agent_to_stage(self, agent_name: str) -> str:
        """
        Convert agent name to workflow stage.
        
        Args:
            agent_name: Agent name
        
        Returns:
            Workflow stage name
        """
        # Reverse lookup in STATE_TO_AGENT
        for stage, agent in self.STATE_TO_AGENT.items():
            if agent == agent_name:
                return stage
        
        # Special mappings
        agent_to_stage_map = {
            "verification": "VERIFICATION",
            "credit_bureau": "CREDIT_ANALYSIS",
            "underwriting": "UNDERWRITING",
            "consolidation": "CONSOLIDATION",
            "sales": "SALES",
            "document": "DOCUMENT"
        }
        
        return agent_to_stage_map.get(agent_name, "INIT")
    
    def get_next_agent(
        self,
        current_agent: str,
        agent_output: Dict[str, Any]
    ) -> Optional[str]:
        """
        Determine next agent based on current agent's output.
        
        Args:
            current_agent: Current agent name
            agent_output: Output from current agent
        
        Returns:
            Next agent name or None if workflow is complete
        """
        # Check if agent explicitly specified next agent
        if "next_agent" in agent_output:
            next_agent = agent_output["next_agent"]
            
            # Validate transition
            current_stage = self._agent_to_stage(current_agent)
            next_stage = self._agent_to_stage(next_agent)
            
            if self._is_valid_transition(current_stage, next_stage):
                return next_agent
            else:
                self.logger.warning(
                    f"Agent {current_agent} suggested invalid next agent {next_agent}"
                )
        
        # Default workflow progression
        workflow_progression = {
            "verification": "credit_bureau",
            "credit_bureau": None,  # Determined by credit analysis
            "underwriting": "sales",
            "consolidation": "sales",
            "sales": "document",
            "document": None  # End of workflow
        }
        
        return workflow_progression.get(current_agent)
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle errors with graceful fallbacks.
        
        Args:
            error: Exception that occurred
            context: Additional context
        
        Returns:
            Error response dictionary
        """
        context = context or {}
        
        self.logger.error(
            f"Master agent error: {str(error)}",
            extra={"context": context},
            exc_info=True
        )
        
        # Categorize error and provide appropriate response
        if isinstance(error, ValidationError):
            return {
                "success": False,
                "message": "I need some additional information. Could you please provide the required details?",
                "error_type": "VALIDATION_ERROR",
                "recoverable": True
            }
        
        elif isinstance(error, AgentError):
            return {
                "success": False,
                "message": error.message if hasattr(error, 'message') else str(error),
                "error_type": error.error_type if hasattr(error, 'error_type') else "AGENT_ERROR",
                "recoverable": error.recoverable if hasattr(error, 'recoverable') else False
            }
        
        else:
            # Unknown error - provide generic fallback
            return {
                "success": False,
                "message": "I apologize, but I encountered an unexpected issue. Please try again or contact support if the problem persists.",
                "error_type": "SYSTEM_ERROR",
                "recoverable": True
            }
    
    def reset_session(self, session_id: str) -> bool:
        """
        Reset a session to initial state.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if successful
        """
        try:
            # Delete old session
            self.session_manager.delete_session(session_id)
            
            # Create new session with same ID (if possible)
            # Otherwise create new one
            new_session_id = self.session_manager.create_session()
            
            self.logger.info(f"Session reset: {session_id} -> {new_session_id}")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to reset session {session_id}: {str(e)}")
            return False
    
    def get_conversation_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary of conversation for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Dictionary with conversation summary or None if session not found
        """
        session = self.session_manager.get_session(session_id)
        
        if session is None:
            return None
        
        history = self.session_manager.get_conversation_history(session_id)
        current_stage = self.session_manager.get_workflow_stage(session_id)
        
        return {
            "session_id": session_id,
            "current_stage": current_stage,
            "message_count": len(history) if history else 0,
            "customer_verified": session.get("state", {}).get("customer_data") is not None,
            "has_offer": session.get("state", {}).get("current_offer") is not None,
            "created_at": session.get("created_at"),
            "last_accessed": session.get("last_accessed")
        }
    
    def process_greeting(self, session_id: str) -> Dict[str, Any]:
        """
        Handle initial greeting and start workflow.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Greeting response
        """
        greeting_message = """Hello! Welcome to Tata Loan Services. I'm here to help you with your personal loan needs.

To get started, I'll need to verify your identity. Please provide:
1. Your PAN card number (format: ABCDE1234F)
2. Your registered mobile number

You can provide both details in your next message."""
        
        # Set workflow stage to VERIFICATION
        self.session_manager.set_workflow_stage(session_id, "VERIFICATION")
        
        # Add greeting to conversation
        self.session_manager.add_conversation_message(
            session_id=session_id,
            role="assistant",
            content=greeting_message,
            agent="master"
        )
        
        return {
            "success": True,
            "message": greeting_message,
            "session_id": session_id,
            "current_stage": "VERIFICATION",
            "agent": "master"
        }


def create_master_agent(
    session_manager: Optional[SessionManager] = None,
    use_mock_llm: bool = False
) -> MasterAgent:
    """
    Factory function to create master agent with dependencies.
    
    Args:
        session_manager: Session manager instance (creates new if None)
        use_mock_llm: Whether to use mock LLM for testing
    
    Returns:
        Configured MasterAgent instance
    """
    if session_manager is None:
        session_manager = SessionManager()
    
    return MasterAgent(
        session_manager=session_manager,
        use_mock_llm=use_mock_llm
    )
