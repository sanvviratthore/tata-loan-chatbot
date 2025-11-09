"""
Unit tests for BaseAgent class.
"""

import pytest
from typing import Dict, Any
from agents.base_agent import (
    BaseAgent, 
    AgentError, 
    ValidationError, 
    DataError, 
    BusinessLogicError,
    SystemError,
    handle_errors,
    validate_input
)
from pydantic import BaseModel, Field


# Create a concrete implementation for testing
class TestAgent(BaseAgent):
    """Test implementation of BaseAgent."""
    
    def __init__(self):
        super().__init__("test_agent")
    
    def process(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Test process implementation."""
        if not self.validate_input(input_data):
            raise ValidationError("Invalid input")
        
        return self.create_response(
            success=True,
            data={"result": "processed"},
            next_agent="next_test_agent"
        )
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Test validation implementation."""
        if not input_data:
            raise ValidationError("Input data cannot be empty")
        
        if "required_field" not in input_data:
            raise ValidationError("Missing required field", field="required_field")
        
        return True


class TestInputSchema(BaseModel):
    """Test schema for input validation."""
    name: str = Field(..., min_length=1)
    age: int = Field(..., gt=0, le=120)


class TestAgentWithSchema(BaseAgent):
    """Test agent with schema validation."""
    
    def __init__(self):
        super().__init__("test_agent_schema")
    
    @validate_input(TestInputSchema)
    def process(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Process with schema validation."""
        return self.create_response(success=True, data={"validated": True})
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Basic validation."""
        return True


def test_base_agent_initialization():
    """Test that BaseAgent initializes correctly."""
    agent = TestAgent()
    
    assert agent.agent_name == "test_agent"
    assert agent.logger is not None
    assert str(agent) == "TestAgent(name='test_agent')"


def test_process_success():
    """Test successful processing."""
    agent = TestAgent()
    
    input_data = {"required_field": "value"}
    session_state = {}
    
    result = agent.process(input_data, session_state)
    
    assert result["success"] is True
    assert result["agent"] == "test_agent"
    assert result["data"]["result"] == "processed"
    assert result["next_agent"] == "next_test_agent"
    assert "timestamp" in result


def test_validation_error():
    """Test validation error handling."""
    agent = TestAgent()
    
    with pytest.raises(ValidationError) as exc_info:
        agent.process({}, {})
    
    assert "Input data cannot be empty" in str(exc_info.value)


def test_validation_error_with_field():
    """Test validation error with field information."""
    agent = TestAgent()
    
    with pytest.raises(ValidationError) as exc_info:
        agent.process({"other_field": "value"}, {})
    
    error = exc_info.value
    assert "Missing required field" in str(error)
    assert error.context.get("field") == "required_field"
    assert error.recoverable is True


def test_handle_error_validation():
    """Test error handling for validation errors."""
    agent = TestAgent()
    error = ValidationError("Invalid format", field="email")
    
    response = agent.handle_error(error)
    
    assert response["success"] is False
    assert response["error_type"] == "VALIDATION_ERROR"
    assert response["recoverable"] is True
    assert "correct information" in response["suggested_action"]


def test_handle_error_data():
    """Test error handling for data errors."""
    agent = TestAgent()
    error = DataError("Customer not found", context={"customer_id": "CUST001"})
    
    response = agent.handle_error(error)
    
    assert response["success"] is False
    assert response["error_type"] == "DATA_ERROR"
    assert response["recoverable"] is False
    assert "customer_id" in response["context"]


def test_handle_error_business_logic():
    """Test error handling for business logic errors."""
    agent = TestAgent()
    error = BusinessLogicError(
        "Too many loans",
        context={"suggested_action": "Reduce existing loans"}
    )
    
    response = agent.handle_error(error)
    
    assert response["success"] is False
    assert response["error_type"] == "BUSINESS_LOGIC_ERROR"
    assert response["recoverable"] is False
    assert response["suggested_action"] == "Reduce existing loans"


def test_handle_error_system():
    """Test error handling for system errors."""
    agent = TestAgent()
    error = SystemError("API timeout")
    
    response = agent.handle_error(error)
    
    assert response["success"] is False
    assert response["error_type"] == "SYSTEM_ERROR"
    assert response["recoverable"] is True
    assert "try again" in response["error_message"].lower()


def test_handle_error_unknown():
    """Test error handling for unknown errors."""
    agent = TestAgent()
    error = Exception("Unknown error")
    
    response = agent.handle_error(error)
    
    assert response["success"] is False
    assert response["error_type"] == "UNKNOWN_ERROR"
    assert response["recoverable"] is True


def test_create_response():
    """Test response creation."""
    agent = TestAgent()
    
    response = agent.create_response(
        success=True,
        data={"key": "value"},
        next_agent="next_agent",
        message="Success message"
    )
    
    assert response["success"] is True
    assert response["agent"] == "test_agent"
    assert response["data"]["key"] == "value"
    assert response["next_agent"] == "next_agent"
    assert response["message"] == "Success message"
    assert "timestamp" in response


def test_create_response_minimal():
    """Test response creation with minimal parameters."""
    agent = TestAgent()
    
    response = agent.create_response(success=False)
    
    assert response["success"] is False
    assert response["agent"] == "test_agent"
    assert "timestamp" in response
    assert "data" not in response
    assert "next_agent" not in response


def test_log_action():
    """Test action logging."""
    agent = TestAgent()
    
    # Should not raise any exceptions
    agent.log_action("test_action", detail="test detail")


def test_log_decision():
    """Test decision logging."""
    agent = TestAgent()
    
    # Should not raise any exceptions
    agent.log_decision(
        decision="approve",
        reasoning="Credit score is high",
        credit_score=750
    )


def test_handle_errors_decorator():
    """Test handle_errors decorator."""
    
    class DecoratorTestAgent(BaseAgent):
        def __init__(self):
            super().__init__("decorator_test")
        
        @handle_errors
        def process(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
            if input_data.get("raise_error"):
                raise ValueError("Test error")
            return {"success": True}
        
        def validate_input(self, input_data: Dict[str, Any]) -> bool:
            return True
    
    agent = DecoratorTestAgent()
    
    # Test successful execution
    result = agent.process({"data": "test"}, {})
    assert result["success"] is True
    
    # Test error conversion
    with pytest.raises(SystemError) as exc_info:
        agent.process({"raise_error": True}, {})
    
    assert "Unexpected error" in str(exc_info.value)


def test_validate_input_decorator():
    """Test validate_input decorator."""
    agent = TestAgentWithSchema()
    
    # Test valid input
    valid_input = {"name": "John", "age": 30}
    result = agent.process(valid_input, {})
    assert result["success"] is True
    
    # Test invalid input
    invalid_input = {"name": "", "age": 30}
    with pytest.raises(ValidationError):
        agent.process(invalid_input, {})


def test_agent_error_attributes():
    """Test AgentError attributes."""
    error = AgentError(
        message="Test error",
        error_type="TEST_ERROR",
        recoverable=True,
        context={"key": "value"}
    )
    
    assert error.message == "Test error"
    assert error.error_type == "TEST_ERROR"
    assert error.recoverable is True
    assert error.context["key"] == "value"


def test_validation_error_defaults():
    """Test ValidationError default values."""
    error = ValidationError("Test validation error")
    
    assert error.error_type == "VALIDATION_ERROR"
    assert error.recoverable is True


def test_data_error_defaults():
    """Test DataError default values."""
    error = DataError("Test data error")
    
    assert error.error_type == "DATA_ERROR"
    assert error.recoverable is False


def test_business_logic_error_defaults():
    """Test BusinessLogicError default values."""
    error = BusinessLogicError("Test business error")
    
    assert error.error_type == "BUSINESS_LOGIC_ERROR"
    assert error.recoverable is False


def test_system_error_defaults():
    """Test SystemError default values."""
    error = SystemError("Test system error")
    
    assert error.error_type == "SYSTEM_ERROR"
    assert error.recoverable is True
