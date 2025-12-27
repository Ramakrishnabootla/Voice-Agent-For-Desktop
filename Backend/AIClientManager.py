#!/usr/bin/env python3
"""
AI Client Manager with Multi-API Fallback Support
Handles multiple Groq API keys and automatic fallback to Gemini API
"""

import os
import time
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from groq import Groq
import google.generativeai as genai
from cohere import Client as CohereClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIClientManager:
    """
    Manages multiple AI API clients with automatic fallback support.
    Priority: Groq (multiple keys) -> Gemini -> Cohere
    """

    def __init__(self):
        self.groq_clients = self._initialize_groq_clients()
        self.gemini_client = self._initialize_gemini_client()
        self.cohere_client = self._initialize_cohere_client()

        # Track API health and usage
        self.api_health = {
            'groq': True,
            'gemini': True,
            'cohere': True
        }

        self.failure_counts = {
            'groq': 0,
            'gemini': 0,
            'cohere': 0
        }

        # Circuit breaker settings
        self.max_failures = 3
        self.circuit_timeout = 300  # 5 minutes

    def _initialize_groq_clients(self) -> List[Groq]:
        """Initialize multiple Groq clients from API keys."""
        groq_clients = []

        # Get multiple Groq API keys
        groq_keys_str = os.getenv('GROQ_API_KEYS', os.getenv('GroqAPI', ''))
        if groq_keys_str:
            groq_keys = [key.strip() for key in groq_keys_str.split(',') if key.strip()]
            for key in groq_keys:
                try:
                    client = Groq(api_key=key)
                    groq_clients.append(client)
                    logger.info(f"Initialized Groq client with key ending in ...{key[-4:]}")
                except Exception as e:
                    logger.error(f"Failed to initialize Groq client: {e}")

        if not groq_clients:
            logger.warning("No valid Groq API keys found")

        return groq_clients

    def _initialize_gemini_client(self) -> Optional[Any]:
        """Initialize Gemini API client."""
        try:
            gemini_key = os.getenv('GeminiAPI', os.getenv('CohereAPI', ''))
            if gemini_key:
                genai.configure(api_key=gemini_key)
                logger.info("Initialized Gemini API client")
                return genai
            else:
                logger.warning("No Gemini API key found")
                return None
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            return None

    def _initialize_cohere_client(self) -> Optional[CohereClient]:
        """Initialize Cohere API client."""
        try:
            cohere_key = os.getenv('CohereAPI')
            if cohere_key:
                client = CohereClient(api_key=cohere_key)
                logger.info("Initialized Cohere API client")
                return client
            else:
                logger.warning("No Cohere API key found")
                return None
        except Exception as e:
            logger.error(f"Failed to initialize Cohere client: {e}")
            return None

    def _is_circuit_open(self, api_name: str) -> bool:
        """Check if circuit breaker is open for an API."""
        if self.failure_counts[api_name] >= self.max_failures:
            # Check if circuit timeout has passed
            if hasattr(self, f'{api_name}_circuit_opened_at'):
                opened_at = getattr(self, f'{api_name}_circuit_opened_at')
                if time.time() - opened_at > self.circuit_timeout:
                    # Reset circuit breaker
                    self.failure_counts[api_name] = 0
                    self.api_health[api_name] = True
                    logger.info(f"Circuit breaker reset for {api_name}")
                    return False
            return True
        return False

    def _record_failure(self, api_name: str):
        """Record API failure and update circuit breaker."""
        self.failure_counts[api_name] += 1
        if self.failure_counts[api_name] >= self.max_failures:
            setattr(self, f'{api_name}_circuit_opened_at', time.time())
            self.api_health[api_name] = False
            logger.warning(f"Circuit breaker opened for {api_name} after {self.failure_counts[api_name]} failures")

    def _record_success(self, api_name: str):
        """Record API success and reset failure count."""
        self.failure_counts[api_name] = 0
        self.api_health[api_name] = True

    def groq_completion(self, messages: List[Dict], model: str = 'llama-3.3-70b-versatile',
                       temperature: float = 0.3, max_tokens: int = 2048,
                       stream: bool = True, **kwargs) -> Optional[str]:
        """
        Try Groq API with multiple keys, return response or None if all fail.
        """
        if not self.groq_clients or self._is_circuit_open('groq'):
            logger.warning("Groq API unavailable (circuit breaker open or no clients)")
            return None

        for i, client in enumerate(self.groq_clients):
            try:
                logger.info(f"Trying Groq client {i+1}/{len(self.groq_clients)}")

                completion = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                    **kwargs
                )

                if stream:
                    answer = ''
                    for chunk in completion:
                        if chunk.choices[0].delta.content:
                            answer += chunk.choices[0].delta.content
                    answer = answer.strip().replace('</s>', '')
                else:
                    answer = completion.choices[0].message.content

                self._record_success('groq')
                logger.info(f"Groq client {i+1} succeeded")
                return answer

            except Exception as e:
                logger.warning(f"Groq client {i+1} failed: {e}")
                continue

        # All Groq clients failed
        self._record_failure('groq')
        logger.error("All Groq API clients failed")
        return None

    def gemini_completion(self, prompt: str, model: str = 'gemini-1.5-flash',
                         temperature: float = 0.3, max_tokens: int = 2048) -> Optional[str]:
        """
        Try Gemini API as fallback.
        """
        if not self.gemini_client or self._is_circuit_open('gemini'):
            logger.warning("Gemini API unavailable")
            return None

        try:
            logger.info("Trying Gemini API")

            model_instance = self.gemini_client.GenerativeModel(model)
            response = model_instance.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )

            answer = response.text.strip()
            self._record_success('gemini')
            logger.info("Gemini API succeeded")
            return answer

        except Exception as e:
            logger.error(f"Gemini API failed: {e}")
            self._record_failure('gemini')
            return None

    def cohere_completion(self, prompt: str, model: str = 'command-r-plus',
                         temperature: float = 0.3, max_tokens: int = 2048) -> Optional[str]:
        """
        Try Cohere API as final fallback.
        """
        if not self.cohere_client or self._is_circuit_open('cohere'):
            logger.warning("Cohere API unavailable")
            return None

        try:
            logger.info("Trying Cohere API")

            response = self.cohere_client.generate(
                model=model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            answer = response.generations[0].text.strip()
            self._record_success('cohere')
            logger.info("Cohere API succeeded")
            return answer

        except Exception as e:
            logger.error(f"Cohere API failed: {e}")
            self._record_failure('cohere')
            return None

    def get_completion_with_fallback(self, messages: List[Dict], prompt: str = None,
                                   model: str = 'llama-3.3-70b-versatile',
                                   temperature: float = 0.3, max_tokens: int = 2048,
                                   stream: bool = True) -> str:
        """
        Get completion with automatic fallback: Groq -> Gemini -> Cohere
        """
        # Convert messages to prompt if needed for non-Groq APIs
        if prompt is None and messages:
            prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

        # Try Groq first (with multiple keys)
        answer = self.groq_completion(messages, model, temperature, max_tokens, stream)
        if answer:
            return answer

        # Fallback to Gemini
        answer = self.gemini_completion(prompt, 'gemini-1.5-flash', temperature, max_tokens)
        if answer:
            return answer

        # Final fallback to Cohere
        answer = self.cohere_completion(prompt, 'command-r-plus', temperature, max_tokens)
        if answer:
            return answer

        # All APIs failed
        return "I'm sorry, all AI services are currently unavailable. Please try again later."

# Global instance
ai_manager = AIClientManager()

def get_ai_response(messages: List[Dict], model: str = 'llama-3.3-70b-versatile',
                   temperature: float = 0.3, max_tokens: int = 2048, stream: bool = True) -> str:
    """
    Convenience function to get AI response with automatic fallback.
    """
    return ai_manager.get_completion_with_fallback(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream
    )

def get_ai_response_from_prompt(prompt: str, model: str = 'llama-3.3-70b-versatile',
                              temperature: float = 0.3, max_tokens: int = 2048) -> str:
    """
    Convenience function to get AI response from prompt with automatic fallback.
    """
    return ai_manager.get_completion_with_fallback(
        messages=[],
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=False
    )

if __name__ == "__main__":
    # Test the AI manager
    test_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]

    response = get_ai_response(test_messages)
    print(f"Response: {response}")