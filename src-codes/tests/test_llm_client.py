"""
Unit tests for LLM client wrapper module.
"""

import pytest
import os
import time
from unittest.mock import Mock, patch, MagicMock
import requests
from utils.llm_client import (
    OpenRouterLLM,
    MockLLM,
    create_llm_client,
    BaseLLM
)


class TestMockLLM:
    """Test cases for MockLLM implementation."""
    
    def test_mock_llm_default_response(self):
        """Test mock LLM returns default response."""
        mock_llm = MockLLM(default_response="Test response")
        
        response = mock_llm.generate("Any prompt")
        
        assert response == "Test response"
        assert mock_llm.call_count == 1
    
    def test_mock_llm_pattern_matching(self):
        """Test mock LLM pattern-based responses."""
        response_map = {
            "greeting": "Hello! How can I help you?",
            "loan": "Here's information about loans.",
            "credit score": "Your credit score is important."
        }
        mock_llm = MockLLM(response_map=response_map)
        
        response1 = mock_llm.generate("I need a greeting")
        assert response1 == "Hello! How can I help you?"
        
        response2 = mock_llm.generate("Tell me about loan options")
        assert response2 == "Here's information about loans."
        
        response3 = mock_llm.generate("What about my credit score?")
        assert response3 == "Your credit score is important."
    
    def test_mock_llm_case_insensitive_matching(self):
        """Test that pattern matching is case-insensitive."""
        response_map = {
            "LOAN": "Loan information"
        }
        mock_llm = MockLLM(response_map=response_map)
        
        response = mock_llm.generate("I need a loan")
        assert response == "Loan information"
    
    def test_mock_llm_call_history(self):
        """Test that mock LLM tracks call history."""
        mock_llm = MockLLM()
        
        mock_llm.generate("First prompt")
        mock_llm.generate("Second prompt", temperature=0.5)
        
        assert mock_llm.call_count == 2
        assert len(mock_llm.call_history) == 2
        assert mock_llm.call_history[0]["prompt"] == "First prompt"
        assert mock_llm.call_history[1]["prompt"] == "Second prompt"
        assert mock_llm.call_history[1]["kwargs"]["temperature"] == 0.5
    
    def test_mock_llm_get_last_prompt(self):
        """Test getting last prompt from mock LLM."""
        mock_llm = MockLLM()
        
        assert mock_llm.get_last_prompt() is None
        
        mock_llm.generate("First prompt")
        assert mock_llm.get_last_prompt() == "First prompt"
        
        mock_llm.generate("Second prompt")
        assert mock_llm.get_last_prompt() == "Second prompt"
    
    def test_mock_llm_reset(self):
        """Test resetting mock LLM state."""
        mock_llm = MockLLM()
        
        mock_llm.generate("Test prompt")
        assert mock_llm.call_count == 1
        
        mock_llm.reset()
        assert mock_llm.call_count == 0
        assert len(mock_llm.call_history) == 0
        assert mock_llm.get_last_prompt() is None


class TestOpenRouterLLM:
    """Test cases for OpenRouterLLM implementation."""
    
    def test_initialization_with_api_key(self):
        """Test OpenRouter LLM initialization with API key."""
        llm = OpenRouterLLM(api_key="test_key_123")
        
        assert llm.api_key == "test_key_123"
        assert llm.model == "meta-llama/llama-3.1-8b-instruct:free"
        assert llm.temperature == 0.7
        assert llm.max_tokens == 500
    
    def test_initialization_from_env_var(self):
        """Test OpenRouter LLM initialization from environment variable."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env_key_456"}):
            llm = OpenRouterLLM()
            assert llm.api_key == "env_key_456"
    
    def test_initialization_without_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenRouter API key not provided"):
                OpenRouterLLM()
    
    def test_custom_parameters(self):
        """Test OpenRouter LLM with custom parameters."""
        llm = OpenRouterLLM(
            api_key="test_key",
            model="custom-model",
            temperature=0.9,
            max_tokens=1000,
            max_retries=3,
            initial_retry_delay=2.0,
            enable_cache=False
        )
        
        assert llm.model == "custom-model"
        assert llm.temperature == 0.9
        assert llm.max_tokens == 1000
        assert llm.max_retries == 3
        assert llm.initial_retry_delay == 2.0
        assert llm.enable_cache is False
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        llm = OpenRouterLLM(api_key="test_key")
        
        key1 = llm._generate_cache_key("Test prompt")
        key2 = llm._generate_cache_key("Test prompt")
        key3 = llm._generate_cache_key("Different prompt")
        
        # Same prompt should generate same key
        assert key1 == key2
        # Different prompt should generate different key
        assert key1 != key3
    
    @patch('requests.post')
    def test_successful_api_request(self, mock_post):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Generated response"}}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        llm = OpenRouterLLM(api_key="test_key")
        response = llm.generate("Test prompt")
        
        assert response == "Generated response"
        assert mock_post.call_count == 1
    
    @patch('requests.post')
    def test_response_caching(self, mock_post):
        """Test that responses are cached."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Cached response"}}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        llm = OpenRouterLLM(api_key="test_key", enable_cache=True)
        
        # First call should hit API
        response1 = llm.generate("Test prompt")
        assert response1 == "Cached response"
        assert mock_post.call_count == 1
        
        # Second call with same prompt should use cache
        response2 = llm.generate("Test prompt")
        assert response2 == "Cached response"
        assert mock_post.call_count == 1  # Still 1, not 2
    
    @patch('requests.post')
    def test_cache_disabled(self, mock_post):
        """Test that caching can be disabled."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Response"}}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        llm = OpenRouterLLM(api_key="test_key", enable_cache=False)
        
        llm.generate("Test prompt")
        llm.generate("Test prompt")
        
        # Should call API twice when cache is disabled
        assert mock_post.call_count == 2
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        llm = OpenRouterLLM(api_key="test_key")
        llm._cache["key1"] = "value1"
        llm._cache["key2"] = "value2"
        
        assert llm.get_cache_size() == 2
        
        llm.clear_cache()
        assert llm.get_cache_size() == 0
    
    @patch('requests.post')
    @patch('time.sleep')
    def test_retry_logic_on_failure(self, mock_sleep, mock_post):
        """Test retry logic with exponential backoff."""
        # First two calls fail, third succeeds
        mock_post.side_effect = [
            requests.exceptions.RequestException("Network error"),
            requests.exceptions.RequestException("Network error"),
            Mock(
                json=lambda: {"choices": [{"message": {"content": "Success"}}]},
                raise_for_status=Mock()
            )
        ]
        
        llm = OpenRouterLLM(api_key="test_key", max_retries=2, initial_retry_delay=1.0)
        response = llm.generate("Test prompt")
        
        assert response == "Success"
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2
        
        # Verify exponential backoff
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] == 1.0
        assert sleep_calls[1] == 2.0
    
    @patch('requests.post')
    def test_all_retries_fail(self, mock_post):
        """Test that exception is raised when all retries fail."""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")
        
        llm = OpenRouterLLM(api_key="test_key", max_retries=2)
        
        with pytest.raises(Exception, match="LLM API call failed after 3 attempts"):
            llm.generate("Test prompt")
        
        assert mock_post.call_count == 3
    
    @patch('requests.post')
    def test_api_request_with_custom_parameters(self, mock_post):
        """Test API request with custom parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Response"}}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        llm = OpenRouterLLM(api_key="test_key")
        llm.generate("Test prompt", temperature=0.9, max_tokens=1000)
        
        # Verify API was called with custom parameters
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["temperature"] == 0.9
        assert payload["max_tokens"] == 1000
    
    @patch('requests.post')
    def test_empty_response_raises_error(self, mock_post):
        """Test that empty response raises ValueError."""
        mock_response = Mock()
        mock_response.json.return_value = {"choices": []}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        llm = OpenRouterLLM(api_key="test_key", max_retries=0)
        
        with pytest.raises(Exception, match="No response generated from LLM"):
            llm.generate("Test prompt")


class TestCreateLLMClient:
    """Test cases for LLM client factory function."""
    
    def test_create_mock_llm(self):
        """Test creating mock LLM client."""
        llm = create_llm_client(use_mock=True)
        
        assert isinstance(llm, MockLLM)
        assert isinstance(llm, BaseLLM)
    
    def test_create_mock_llm_with_responses(self):
        """Test creating mock LLM with custom responses."""
        responses = {"test": "Test response"}
        llm = create_llm_client(use_mock=True, mock_responses=responses)
        
        assert isinstance(llm, MockLLM)
        response = llm.generate("This is a test")
        assert response == "Test response"
    
    def test_create_openrouter_llm(self):
        """Test creating OpenRouter LLM client."""
        llm = create_llm_client(use_mock=False, api_key="test_key")
        
        assert isinstance(llm, OpenRouterLLM)
        assert isinstance(llm, BaseLLM)
    
    def test_create_openrouter_llm_with_custom_params(self):
        """Test creating OpenRouter LLM with custom parameters."""
        llm = create_llm_client(
            use_mock=False,
            api_key="test_key",
            model="custom-model",
            temperature=0.8
        )
        
        assert isinstance(llm, OpenRouterLLM)
        assert llm.model == "custom-model"
        assert llm.temperature == 0.8


class TestIntegrationScenarios:
    """Integration tests for realistic usage scenarios."""
    
    def test_mock_llm_for_testing_agents(self):
        """Test using mock LLM for agent testing."""
        # Simulate agent responses
        agent_responses = {
            "intent": "loan_inquiry",
            "greeting": "Hello! I'm here to help with your loan application.",
            "consolidation": "Based on your profile, consolidation could save you money."
        }
        
        llm = MockLLM(response_map=agent_responses)
        
        # Test intent detection
        intent = llm.generate("Classify intent: I need a loan")
        assert intent == "loan_inquiry"
        
        # Test greeting
        greeting = llm.generate("Generate greeting for user")
        assert greeting == "Hello! I'm here to help with your loan application."
        
        # Test consolidation advice
        advice = llm.generate("Provide consolidation recommendation")
        assert advice == "Based on your profile, consolidation could save you money."
        
        assert llm.call_count == 3
    
    @patch('requests.post')
    def test_openrouter_with_retry_recovery(self, mock_post):
        """Test OpenRouter LLM recovering from transient failures."""
        # Simulate transient network issue followed by success
        mock_post.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            Mock(
                json=lambda: {"choices": [{"message": {"content": "Recovered response"}}]},
                raise_for_status=Mock()
            )
        ]
        
        llm = OpenRouterLLM(api_key="test_key", max_retries=2)
        response = llm.generate("Test prompt")
        
        assert response == "Recovered response"
        assert mock_post.call_count == 2
