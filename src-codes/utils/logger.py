"""
Logging Configuration Module

Provides structured JSON logging with file rotation and agent-specific decorators.
"""

import logging
import json
import os
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional, Callable
from logging.handlers import RotatingFileHandler
import traceback


# Log levels
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs in JSON format."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
        
        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


def setup_logger(
    name: str,
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    console_output: bool = True,
    json_format: bool = True
) -> logging.Logger:
    """
    Set up and configure a logger with file rotation and JSON formatting.
    
    Args:
        name: Logger name (typically module name)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional, defaults to logs/{name}.log)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        console_output: Whether to output logs to console
        json_format: Whether to use JSON formatting
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Add file handler with rotation if log file specified
    if log_file:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with default configuration.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # If logger has no handlers, set it up with defaults
    if not logger.handlers:
        log_level = os.getenv("LOG_LEVEL", "INFO")
        log_dir = os.getenv("LOG_DIR", "logs")
        log_file = os.path.join(log_dir, f"{name}.log")
        
        setup_logger(
            name=name,
            log_level=log_level,
            log_file=log_file,
            console_output=True,
            json_format=True
        )
    
    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs):
    """
    Log a message with additional context fields.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **kwargs: Additional context fields to include in log
    """
    # Get the appropriate log function
    log_func = getattr(logger, level.lower())
    
    # Pass extra fields through the extra parameter
    # The JSONFormatter will look for extra_fields attribute
    class ExtraAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs_inner):
            if 'extra' not in kwargs_inner:
                kwargs_inner['extra'] = {}
            kwargs_inner['extra']['extra_fields'] = self.extra
            return msg, kwargs_inner
    
    adapter = ExtraAdapter(logger, kwargs)
    adapter_func = getattr(adapter, level.lower())
    adapter_func(message)


def log_agent_execution(agent_name: str):
    """
    Decorator for logging agent execution with timing and error handling.
    
    Args:
        agent_name: Name of the agent being executed
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = get_logger(f"agent.{agent_name}")
            
            # Log execution start
            start_time = datetime.utcnow()
            log_with_context(
                logger,
                "info",
                f"Agent execution started: {agent_name}",
                agent=agent_name,
                function=func.__name__,
                start_time=start_time.isoformat()
            )
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log successful completion
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                log_with_context(
                    logger,
                    "info",
                    f"Agent execution completed: {agent_name}",
                    agent=agent_name,
                    function=func.__name__,
                    duration_seconds=duration,
                    status="success"
                )
                
                return result
                
            except Exception as e:
                # Log error
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                log_with_context(
                    logger,
                    "error",
                    f"Agent execution failed: {agent_name}",
                    agent=agent_name,
                    function=func.__name__,
                    duration_seconds=duration,
                    status="error",
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                
                # Re-raise the exception
                raise
        
        return wrapper
    return decorator


def log_function_call(logger_name: Optional[str] = None):
    """
    Decorator for logging function calls with parameters and return values.
    
    Args:
        logger_name: Name of logger to use (defaults to module name)
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get logger
            log_name = logger_name or func.__module__
            logger = get_logger(log_name)
            
            # Log function call
            log_with_context(
                logger,
                "debug",
                f"Function called: {func.__name__}",
                function=func.__name__,
                args=str(args)[:200],  # Truncate long args
                kwargs=str(kwargs)[:200]
            )
            
            try:
                result = func(*args, **kwargs)
                
                # Log return value
                log_with_context(
                    logger,
                    "debug",
                    f"Function returned: {func.__name__}",
                    function=func.__name__,
                    return_value=str(result)[:200]
                )
                
                return result
                
            except Exception as e:
                # Log exception
                logger.error(
                    f"Function raised exception: {func.__name__}",
                    exc_info=True,
                    extra={"extra_fields": {
                        "function": func.__name__,
                        "error_type": type(e).__name__
                    }}
                )
                raise
        
        return wrapper
    return decorator


def log_session_event(session_id: str, event_type: str, **kwargs):
    """
    Log a session-related event with context.
    
    Args:
        session_id: Session identifier
        event_type: Type of event (created, updated, deleted, etc.)
        **kwargs: Additional event context
    """
    logger = get_logger("session")
    
    log_with_context(
        logger,
        "info",
        f"Session event: {event_type}",
        session_id=session_id,
        event_type=event_type,
        **kwargs
    )


def log_llm_request(model: str, prompt: str, response: Optional[str] = None, 
                   error: Optional[str] = None, duration: Optional[float] = None):
    """
    Log an LLM API request with details.
    
    Args:
        model: Model name used
        prompt: Prompt sent to LLM (truncated)
        response: Response from LLM (truncated, optional)
        error: Error message if request failed (optional)
        duration: Request duration in seconds (optional)
    """
    logger = get_logger("llm")
    
    context = {
        "model": model,
        "prompt_length": len(prompt),
        "prompt_preview": prompt[:100]
    }
    
    if response:
        context["response_length"] = len(response)
        context["response_preview"] = response[:100]
    
    if error:
        context["error"] = error
    
    if duration:
        context["duration_seconds"] = duration
    
    level = "error" if error else "info"
    message = "LLM request failed" if error else "LLM request completed"
    
    log_with_context(logger, level, message, **context)


def log_workflow_transition(session_id: str, from_stage: str, to_stage: str, 
                           agent: Optional[str] = None):
    """
    Log a workflow stage transition.
    
    Args:
        session_id: Session identifier
        from_stage: Previous workflow stage
        to_stage: New workflow stage
        agent: Agent handling the transition (optional)
    """
    logger = get_logger("workflow")
    
    context = {
        "session_id": session_id,
        "from_stage": from_stage,
        "to_stage": to_stage
    }
    
    if agent:
        context["agent"] = agent
    
    log_with_context(
        logger,
        "info",
        f"Workflow transition: {from_stage} -> {to_stage}",
        **context
    )


# Initialize default loggers
def initialize_logging(log_level: str = "INFO", log_dir: str = "logs"):
    """
    Initialize all application loggers with consistent configuration.
    
    Args:
        log_level: Default log level for all loggers
        log_dir: Directory for log files
    """
    # Set environment variables
    os.environ["LOG_LEVEL"] = log_level
    os.environ["LOG_DIR"] = log_dir
    
    # Create log directory
    os.makedirs(log_dir, exist_ok=True)
    
    # Initialize main application loggers
    logger_names = [
        "app",
        "agent",
        "session",
        "llm",
        "workflow",
        "database"
    ]
    
    for name in logger_names:
        get_logger(name)
