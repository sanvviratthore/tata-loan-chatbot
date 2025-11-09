"""
Unit tests for logging configuration module.
"""

import pytest
import logging
import json
import os
import tempfile
import shutil
from datetime import datetime
from utils.logger import (
    JSONFormatter,
    setup_logger,
    get_logger,
    log_with_context,
    log_agent_execution,
    log_function_call,
    log_session_event,
    log_llm_request,
    log_workflow_transition,
    initialize_logging
)


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def clean_loggers():
    """Clean up loggers after each test."""
    yield
    # Clear all handlers from loggers
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)


class TestJSONFormatter:
    """Test cases for JSON formatter."""
    
    def test_json_formatter_basic(self):
        """Test basic JSON formatting."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["logger"] == "test"
        assert "timestamp" in log_data
    
    def test_json_formatter_with_exception(self):
        """Test JSON formatting with exception info."""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=exc_info
            )
            
            formatted = formatter.format(record)
            log_data = json.loads(formatted)
            
            assert "exception" in log_data
            assert log_data["exception"]["type"] == "ValueError"
            assert "Test error" in log_data["exception"]["message"]
    
    def test_json_formatter_with_extra_fields(self):
        """Test JSON formatting with extra context fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.extra_fields = {"user_id": "123", "session_id": "abc"}
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["user_id"] == "123"
        assert log_data["session_id"] == "abc"


class TestSetupLogger:
    """Test cases for logger setup."""
    
    def test_setup_logger_basic(self, temp_log_dir, clean_loggers):
        """Test basic logger setup."""
        log_file = os.path.join(temp_log_dir, "test.log")
        logger = setup_logger("test_logger", log_file=log_file)
        
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0
    
    def test_setup_logger_with_custom_level(self, temp_log_dir, clean_loggers):
        """Test logger setup with custom log level."""
        log_file = os.path.join(temp_log_dir, "test.log")
        logger = setup_logger("test_logger", log_level="DEBUG", log_file=log_file)
        
        assert logger.level == logging.DEBUG
    
    def test_setup_logger_creates_directory(self, temp_log_dir, clean_loggers):
        """Test that logger setup creates log directory."""
        log_file = os.path.join(temp_log_dir, "subdir", "test.log")
        logger = setup_logger("test_logger", log_file=log_file)
        
        assert os.path.exists(os.path.dirname(log_file))
    
    def test_setup_logger_file_rotation(self, temp_log_dir, clean_loggers):
        """Test logger with file rotation."""
        log_file = os.path.join(temp_log_dir, "test.log")
        logger = setup_logger(
            "test_logger",
            log_file=log_file,
            max_bytes=1024,
            backup_count=3
        )
        
        # Check that rotating file handler is configured
        from logging.handlers import RotatingFileHandler
        handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
        assert len(handlers) > 0
        assert handlers[0].maxBytes == 1024
        assert handlers[0].backupCount == 3
    
    def test_setup_logger_console_output(self, clean_loggers):
        """Test logger with console output."""
        logger = setup_logger("test_logger", console_output=True)
        
        # Check that stream handler is present
        stream_handlers = [h for h in logger.handlers 
                          if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) > 0
    
    def test_setup_logger_no_console_output(self, temp_log_dir, clean_loggers):
        """Test logger without console output."""
        log_file = os.path.join(temp_log_dir, "test.log")
        logger = setup_logger("test_logger", log_file=log_file, console_output=False)
        
        # Check that only file handler is present
        from logging.handlers import RotatingFileHandler
        assert all(isinstance(h, RotatingFileHandler) for h in logger.handlers)


class TestGetLogger:
    """Test cases for get_logger function."""
    
    def test_get_logger_creates_new(self, clean_loggers):
        """Test that get_logger creates a new logger."""
        logger = get_logger("test_logger")
        
        assert logger.name == "test_logger"
        assert len(logger.handlers) > 0
    
    def test_get_logger_returns_existing(self, clean_loggers):
        """Test that get_logger returns existing logger."""
        logger1 = get_logger("test_logger")
        logger2 = get_logger("test_logger")
        
        assert logger1 is logger2
    
    def test_get_logger_respects_env_vars(self, temp_log_dir, clean_loggers):
        """Test that get_logger respects environment variables."""
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["LOG_DIR"] = temp_log_dir
        
        logger = get_logger("test_logger")
        
        assert logger.level == logging.DEBUG
        
        # Clean up
        del os.environ["LOG_LEVEL"]
        del os.environ["LOG_DIR"]


class TestLogWithContext:
    """Test cases for log_with_context function."""
    
    def test_log_with_context(self, temp_log_dir, clean_loggers):
        """Test logging with additional context."""
        log_file = os.path.join(temp_log_dir, "test.log")
        logger = setup_logger("test_logger", log_file=log_file, console_output=False)
        
        log_with_context(
            logger,
            "info",
            "Test message",
            user_id="123",
            action="login"
        )
        
        # Read log file and verify context
        with open(log_file, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            
            assert log_data["message"] == "Test message"
            assert log_data["user_id"] == "123"
            assert log_data["action"] == "login"


class TestLogAgentExecution:
    """Test cases for log_agent_execution decorator."""
    
    def test_log_agent_execution_success(self, temp_log_dir, clean_loggers):
        """Test agent execution logging for successful execution."""
        os.environ["LOG_DIR"] = temp_log_dir
        log_file = os.path.join(temp_log_dir, "agent.test_agent.log")
        
        @log_agent_execution("test_agent")
        def test_function():
            return "success"
        
        result = test_function()
        
        assert result == "success"
        assert os.path.exists(log_file)
        
        # Verify log contents
        with open(log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 2  # Start and completion logs
            
            start_log = json.loads(lines[0])
            assert "started" in start_log["message"]
            assert start_log["agent"] == "test_agent"
            
            end_log = json.loads(lines[-1])
            assert "completed" in end_log["message"]
            assert end_log["status"] == "success"
    
    def test_log_agent_execution_error(self, temp_log_dir, clean_loggers):
        """Test agent execution logging for failed execution."""
        os.environ["LOG_DIR"] = temp_log_dir
        log_file = os.path.join(temp_log_dir, "agent.test_agent.log")
        
        @log_agent_execution("test_agent")
        def test_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            test_function()
        
        assert os.path.exists(log_file)
        
        # Verify error log
        with open(log_file, 'r') as f:
            lines = f.readlines()
            error_log = json.loads(lines[-1])
            
            assert "failed" in error_log["message"]
            assert error_log["status"] == "error"
            assert error_log["error_type"] == "ValueError"


class TestLogFunctionCall:
    """Test cases for log_function_call decorator."""
    
    def test_log_function_call_success(self, temp_log_dir, clean_loggers):
        """Test function call logging."""
        @log_function_call("test_module")
        def test_function(x, y):
            return x + y
        
        result = test_function(2, 3)
        
        assert result == 5
    
    def test_log_function_call_with_exception(self, temp_log_dir, clean_loggers):
        """Test function call logging with exception."""
        @log_function_call("test_module")
        def test_function():
            raise RuntimeError("Test error")
        
        with pytest.raises(RuntimeError):
            test_function()


class TestLogSessionEvent:
    """Test cases for log_session_event function."""
    
    def test_log_session_event(self, temp_log_dir, clean_loggers):
        """Test session event logging."""
        os.environ["LOG_DIR"] = temp_log_dir
        log_file = os.path.join(temp_log_dir, "session.log")
        
        log_session_event(
            session_id="session_123",
            event_type="created",
            user_id="user_456"
        )
        
        assert os.path.exists(log_file)
        
        with open(log_file, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            
            assert log_data["session_id"] == "session_123"
            assert log_data["event_type"] == "created"
            assert log_data["user_id"] == "user_456"


class TestLogLLMRequest:
    """Test cases for log_llm_request function."""
    
    def test_log_llm_request_success(self, temp_log_dir, clean_loggers):
        """Test LLM request logging for successful request."""
        os.environ["LOG_DIR"] = temp_log_dir
        log_file = os.path.join(temp_log_dir, "llm.log")
        
        log_llm_request(
            model="gpt-4",
            prompt="Test prompt",
            response="Test response",
            duration=1.5
        )
        
        assert os.path.exists(log_file)
        
        with open(log_file, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            
            assert log_data["model"] == "gpt-4"
            assert log_data["prompt_length"] == len("Test prompt")
            assert log_data["response_length"] == len("Test response")
            assert log_data["duration_seconds"] == 1.5
    
    def test_log_llm_request_error(self, temp_log_dir, clean_loggers):
        """Test LLM request logging for failed request."""
        os.environ["LOG_DIR"] = temp_log_dir
        log_file = os.path.join(temp_log_dir, "llm.log")
        
        log_llm_request(
            model="gpt-4",
            prompt="Test prompt",
            error="API timeout"
        )
        
        assert os.path.exists(log_file)
        
        with open(log_file, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            
            assert log_data["level"] == "ERROR"
            assert log_data["error"] == "API timeout"


class TestLogWorkflowTransition:
    """Test cases for log_workflow_transition function."""
    
    def test_log_workflow_transition(self, temp_log_dir, clean_loggers):
        """Test workflow transition logging."""
        os.environ["LOG_DIR"] = temp_log_dir
        log_file = os.path.join(temp_log_dir, "workflow.log")
        
        log_workflow_transition(
            session_id="session_123",
            from_stage="greeting",
            to_stage="information_gathering",
            agent="router_agent"
        )
        
        assert os.path.exists(log_file)
        
        with open(log_file, 'r') as f:
            log_line = f.readline()
            log_data = json.loads(log_line)
            
            assert log_data["session_id"] == "session_123"
            assert log_data["from_stage"] == "greeting"
            assert log_data["to_stage"] == "information_gathering"
            assert log_data["agent"] == "router_agent"


class TestInitializeLogging:
    """Test cases for initialize_logging function."""
    
    def test_initialize_logging(self, temp_log_dir, clean_loggers):
        """Test logging initialization."""
        initialize_logging(log_level="DEBUG", log_dir=temp_log_dir)
        
        # Verify environment variables are set
        assert os.environ["LOG_LEVEL"] == "DEBUG"
        assert os.environ["LOG_DIR"] == temp_log_dir
        
        # Verify log directory exists
        assert os.path.exists(temp_log_dir)
        
        # Verify loggers are initialized
        logger = logging.getLogger("app")
        assert len(logger.handlers) > 0
        
        # Clean up
        del os.environ["LOG_LEVEL"]
        del os.environ["LOG_DIR"]


class TestIntegrationScenarios:
    """Integration tests for logging in realistic scenarios."""
    
    def test_complete_logging_workflow(self, temp_log_dir, clean_loggers):
        """Test complete logging workflow with multiple components."""
        initialize_logging(log_level="INFO", log_dir=temp_log_dir)
        
        # Log session creation
        log_session_event("session_123", "created", user_id="user_456")
        
        # Log workflow transition
        log_workflow_transition(
            "session_123",
            "greeting",
            "information_gathering"
        )
        
        # Log LLM request
        log_llm_request(
            model="gpt-4",
            prompt="What is your loan requirement?",
            response="I need a personal loan",
            duration=0.8
        )
        
        # Verify all log files exist
        assert os.path.exists(os.path.join(temp_log_dir, "session.log"))
        assert os.path.exists(os.path.join(temp_log_dir, "workflow.log"))
        assert os.path.exists(os.path.join(temp_log_dir, "llm.log"))
        
        # Clean up
        del os.environ["LOG_LEVEL"]
        del os.environ["LOG_DIR"]
