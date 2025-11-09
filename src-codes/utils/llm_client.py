"""
LLM Client Wrapper Module

Provides OpenRouter API integration with retry logic, exponential backoff, and response caching.
"""

import os
import time
import hashlib
import json
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import requests


class BaseLLM(ABC):
    """Abstract base class for LLM implementations."""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from LLM."""
        pass


class OpenRouterLLM(BaseLLM):
    """
    OpenRouter API client with retry logic and caching.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "mistralai/mistral-7b-instruct:free",
        base_url: str = "https://openrouter.ai/api/v1",
        temperature: float = 0.7,
        max_tokens: int = 500,
        max_retries: int = 2,
        initial_retry_delay: float = 1.0,
        enable_cache: bool = True
    ):
        """
        Initialize OpenRouter LLM client.
        
        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            model: Model identifier to use
            base_url: OpenRouter API base URL
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            max_retries: Maximum number of retry attempts
            initial_retry_delay: Initial delay in seconds for exponential backoff
            enable_cache: Whether to enable response caching
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not provided. Set OPENROUTER_API_KEY environment variable.")
        
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.enable_cache = enable_cache
        
        # Response cache
        self._cache: Dict[str, str] = {}
    
    def _generate_cache_key(self, prompt: str, **kwargs) -> str:
        """
        Generate cache key from prompt and parameters.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters
        
        Returns:
            MD5 hash of prompt and parameters
        """
        cache_data = {
            "prompt": prompt,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **kwargs
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _make_api_request(self, prompt: str, **kwargs) -> str:
        """
        Make API request to OpenRouter.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters to override defaults
        
        Returns:
            Generated text response
        
        Raises:
            requests.exceptions.RequestException: If API request fails
        """
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/tata-loan-chatbot",
            "X-Title": "Tata Loan Chatbot"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens)
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Log the error details for debugging
            error_detail = ""
            try:
                error_data = response.json()
                error_detail = f" - {error_data.get('error', {}).get('message', str(error_data))}"
            except:
                error_detail = f" - {response.text[:200]}"
            raise requests.exceptions.HTTPError(f"{e}{error_detail}", response=response)
        
        data = response.json()
        
        if "choices" not in data or len(data["choices"]) == 0:
            raise ValueError("No response generated from LLM")
        
        return data["choices"][0]["message"]["content"].strip()
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate response from LLM with retry logic and caching.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            Generated text response
        
        Raises:
            Exception: If all retry attempts fail
        """
        # Check cache first
        if self.enable_cache:
            cache_key = self._generate_cache_key(prompt, **kwargs)
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        # Attempt API call with exponential backoff
        last_exception = None
        retry_delay = self.initial_retry_delay
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self._make_api_request(prompt, **kwargs)
                
                # Cache successful response
                if self.enable_cache:
                    cache_key = self._generate_cache_key(prompt, **kwargs)
                    self._cache[cache_key] = response
                
                return response
            
            except requests.exceptions.RequestException as e:
                last_exception = e
                
                # Don't retry on last attempt
                if attempt < self.max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    break
        
        # All retries failed
        raise Exception(f"LLM API call failed after {self.max_retries + 1} attempts: {last_exception}")
    
    def clear_cache(self):
        """Clear the response cache."""
        self._cache.clear()
    
    def get_cache_size(self) -> int:
        """Get number of cached responses."""
        return len(self._cache)


class MockLLM(BaseLLM):
    """
    Mock LLM implementation for testing.
    
    Returns predefined responses based on prompt patterns.
    """
    
    def __init__(self, response_map: Optional[Dict[str, str]] = None, default_response: str = "Mock LLM response"):
        """
        Initialize mock LLM.
        
        Args:
            response_map: Dictionary mapping prompt patterns to responses
            default_response: Default response when no pattern matches
        """
        self.response_map = response_map or {}
        self.default_response = default_response
        self.call_count = 0
        self.call_history = []
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate mock response based on prompt pattern.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters (ignored)
        
        Returns:
            Mock response string
        """
        self.call_count += 1
        self.call_history.append({
            "prompt": prompt,
            "kwargs": kwargs,
            "timestamp": time.time()
        })
        
        # Check for pattern matches
        for pattern, response in self.response_map.items():
            if pattern.lower() in prompt.lower():
                return response
        
        return self.default_response
    
    def reset(self):
        """Reset call count and history."""
        self.call_count = 0
        self.call_history.clear()
    
    def get_last_prompt(self) -> Optional[str]:
        """Get the last prompt sent to the mock LLM."""
        if self.call_history:
            return self.call_history[-1]["prompt"]
        return None


def create_llm_client(
    use_mock: bool = False,
    mock_responses: Optional[Dict[str, str]] = None,
    **kwargs
) -> BaseLLM:
    """
    Factory function to create LLM client.
    
    Args:
        use_mock: Whether to use mock LLM (for testing)
        mock_responses: Response map for mock LLM
        **kwargs: Additional parameters for OpenRouter LLM
    
    Returns:
        LLM client instance (OpenRouterLLM or MockLLM)
    """
    if use_mock:
        return MockLLM(response_map=mock_responses)
    else:
        return OpenRouterLLM(**kwargs)
