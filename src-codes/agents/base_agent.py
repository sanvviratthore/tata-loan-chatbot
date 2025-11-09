"""
Base Agent Class

Abstract base class for all specialized agents in the loan chatbot system.
Provides common interface, logging, and error handling functionality.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
from functools import wraps
from datetime import datetime
import traceback

from utils.logger import get_logger, log_with_context, log_agent_execution
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError


class AgentError(Exception):
    """Base exception for agent-related errors."""
    
    def __init__(self, message: str, error_type: str = "AGENT_ERROR", 
                 recoverable: bool = False, context: Optional[Dict] = None):
        """
        Initialize agent error.
        
        Args:
            message: Error message
            error_type: Type of error for categorization
            recoverable: Whether the error is recoverable with retry
            context: Additional context about the error
        """
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.recoverable = recoverable
        self.context = context or {}


class ValidationError(AgentError):
    """Error for input validation failures."""
    
    def __init__(self, message: str, field: Optional[str] = None, context: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_type="VALIDATION_ERROR",
            recoverable=True,
            context={"field": field, **(context or {})}
        )


class DataError(AgentError):
    """Error for data retrieval or processing failures."""
    
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_type="DATA_ERROR",
            recoverable=False,
            context=context
        )


class BusinessLogicError(AgentError):
    """Error for business rule violations."""
    
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_type="BUSINESS_LOGIC_ERROR",
            recoverable=False,
            context=context
        )


class SystemError(AgentError):
    """Error for system-level failures."""
    
    def __init__(self, message: str, context: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_type="SYSTEM_ERROR",
            recoverable=True,
            context=context
        )


def handle_errors(func: Callable) -> Callable:
    """
    Decorator for standardized error handling in agent methods.
    
    Catches exceptions, logs them, and converts to AgentError if needed.
    
    Args:
        func: Function to wrap
    
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs) -> Any:
        try:
            return func(self, *args, **kwargs)
        
        except AgentError:
            # Re-raise AgentError as-is
            raise
        
        except PydanticValidationError as e:
            # Convert Pydantic validation errors
            error_msg = f"Validation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise ValidationError(error_msg, context={"original_error": str(e)})
        
        except FileNotFoundError as e:
            # Handle missing data files
            error_msg = f"Required data file not found: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise DataError(error_msg, context={"file": str(e)})
        
        except KeyError as e:
            # Handle missing data keys
            error_msg = f"Required data key not found: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise DataError(error_msg, context={"key": str(e)})
        
        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = f"Unexpected error in {func.__name__}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise SystemError(error_msg, context={
                "function": func.__name__,
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            })
    
    return wrapper


def validate_input(schema: type[BaseModel]):
    """
    Decorator for validating input against a Pydantic schema.
    
    Args:
        schema: Pydantic model class to validate against
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            # If first argument is a dict, validate it
            if args and isinstance(args[0], dict):
                try:
                    validated_data = schema(**args[0])
                    # Replace first arg with validated model
                    args = (validated_data,) + args[1:]
                except PydanticValidationError as e:
                    error_msg = f"Input validation failed for {schema.__name__}: {str(e)}"
                    self.logger.error(error_msg)
                    raise ValidationError(error_msg, context={"schema": schema.__name__})
            
            return func(self, *args, **kwargs)
        
        return wrapper
    return decorator


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    
    Provides common functionality:
    - Logging configuration
    - Error handling
    - Input validation
    - Standard interface methods
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize base agent.
        
        Args:
            agent_name: Name of the agent (used for logging)
        """
        self.agent_name = agent_name
        self.logger = get_logger(f"agent.{agent_name}")
        
        # Log agent initialization
        log_with_context(
            self.logger,
            "info",
            f"Agent initialized: {agent_name}",
            agent=agent_name,
            timestamp=datetime.utcnow().isoformat()
        )
    
    @abstractmethod
    @handle_errors
    def process(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method for the agent.
        
        This method must be implemented by all concrete agent classes.
        
        Args:
            input_data: Input data for processing
            session_state: Current session state
        
        Returns:
            Dictionary containing:
                - success: bool indicating if processing succeeded
                - data: Processed output data
                - next_agent: Name of next agent to route to (optional)
                - error: Error message if failed (optional)
        
        Raises:
            AgentError: If processing fails
        """
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data before processing.
        
        This method must be implemented by all concrete agent classes.
        
        Args:
            input_data: Input data to validate
        
        Returns:
            True if validation passes
        
        Raises:
            ValidationError: If validation fails
        """
        pass
    
    def handle_error(self, error: Exception, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Handle errors and generate user-friendly responses.
        
        Args:
            error: Exception that occurred
            context: Additional context about the error
        
        Returns:
            Dictionary containing error response:
                - success: False
                - error_type: Type of error
                - error_message: User-friendly error message
                - recoverable: Whether error is recoverable
                - suggested_action: Suggested action for user
        """
        context = context or {}
        
        # Log the error
        log_with_context(
            self.logger,
            "error",
            f"Error in {self.agent_name}: {str(error)}",
            agent=self.agent_name,
            error_type=type(error).__name__,
            error_message=str(error),
            **context
        )
        
        # Generate response based on error type
        if isinstance(error, ValidationError):
            return {
                "success": False,
                "error_type": "VALIDATION_ERROR",
                "error_message": self._get_user_friendly_message(error),
                "recoverable": True,
                "suggested_action": "Please provide the correct information and try again.",
                "context": error.context
            }
        
        elif isinstance(error, DataError):
            return {
                "success": False,
                "error_type": "DATA_ERROR",
                "error_message": "We couldn't retrieve your information. Please try again later.",
                "recoverable": False,
                "suggested_action": "Contact support if the issue persists.",
                "context": error.context
            }
        
        elif isinstance(error, BusinessLogicError):
            return {
                "success": False,
                "error_type": "BUSINESS_LOGIC_ERROR",
                "error_message": self._get_user_friendly_message(error),
                "recoverable": False,
                "suggested_action": error.context.get("suggested_action", "Please review the requirements."),
                "context": error.context
            }
        
        elif isinstance(error, SystemError):
            return {
                "success": False,
                "error_type": "SYSTEM_ERROR",
                "error_message": "A system error occurred. Please try again.",
                "recoverable": True,
                "suggested_action": "Retry your request. Contact support if the issue persists.",
                "context": error.context
            }
        
        else:
            # Unknown error type
            return {
                "success": False,
                "error_type": "UNKNOWN_ERROR",
                "error_message": "An unexpected error occurred. Please try again.",
                "recoverable": True,
                "suggested_action": "Retry your request. Contact support if the issue persists.",
                "context": {"original_error": str(error)}
            }
    
    def _get_user_friendly_message(self, error: AgentError) -> str:
        """
        Convert technical error message to user-friendly message.
        
        Args:
            error: Agent error
        
        Returns:
            User-friendly error message
        """
        # Override in subclasses for agent-specific messages
        return error.message
    
    def log_action(self, action: str, **kwargs):
        """
        Log an agent action with context.
        
        Args:
            action: Action being performed
            **kwargs: Additional context
        """
        log_with_context(
            self.logger,
            "info",
            f"Agent action: {action}",
            agent=self.agent_name,
            action=action,
            **kwargs
        )
    
    def log_decision(self, decision: str, reasoning: str, **kwargs):
        """
        Log an agent decision with reasoning.
        
        Args:
            decision: Decision made
            reasoning: Reasoning behind the decision
            **kwargs: Additional context
        """
        log_with_context(
            self.logger,
            "info",
            f"Agent decision: {decision}",
            agent=self.agent_name,
            decision=decision,
            reasoning=reasoning,
            **kwargs
        )
    
    def create_response(self, success: bool, data: Optional[Dict] = None, 
                       next_agent: Optional[str] = None, 
                       message: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a standardized response dictionary.
        
        Args:
            success: Whether the operation succeeded
            data: Response data
            next_agent: Name of next agent to route to
            message: Optional message for the user
        
        Returns:
            Standardized response dictionary
        """
        response = {
            "success": success,
            "agent": self.agent_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if data is not None:
            response["data"] = data
        
        if next_agent is not None:
            response["next_agent"] = next_agent
        
        if message is not None:
            response["message"] = message
        
        return response
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(name='{self.agent_name}')"
