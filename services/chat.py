from api.models import ChatRequest, ChatResponse
from llm import deepseek_client
from config import settings
from config.logging_config import get_logger
from cache import cache
from typing import Optional
import json
import hashlib
import time
import socket
import openai


logger = get_logger('llm_service.chat')

class InvalidResponseFormat(Exception):
    """Invalid Response Format From LLM"""

class EmptyResponse(Exception):
    """Empty Response From LLM"""

class ChatService:
    """Service for handling chat interactions with LLM."""

    def __init__(self, client=None, settings_obj=None, cache_client=None):
        self.client = client or deepseek_client
        self.settings = settings_obj or settings
        self.cache = cache_client or cache

    def _generate_cache_key(self, request: ChatRequest, temperature: float, max_output_tokens: int, system_prompt: str, model: str) -> str:
        key_data = {
            "dish": request.dish,
            "people": request.people,
            "use_steps": request.use_steps,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "system_prompt": system_prompt,
            "model_name" : model
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return f"chat:{hashlib.md5(key_str.encode()).hexdigest()}"

    def _parse_llm_response(self, response: str, use_steps: bool) -> dict:
        """Parse LLM response and extract products and steps fields."""
        try:
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                response = match.group(0)
            data = json.loads(response)
            result = {}

            for key in ['products', 'продукты', 'ингредиенты', 'ingredients']:
                if key in data:
                    for item in data[key]:
                        if item.strip():
                            result.setdefault('products', []).append(item)

            if use_steps:
                for key in ['steps', 'шаги', 'instructions', 'instruction']:
                    if key in data:
                        for item in data[key]:
                            if item.strip():
                                result.setdefault('steps', []).append(item)

            if not result.get('products'):
                raise EmptyResponse()

            return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON", extra={"event": "PARSE_ERROR", "response_preview": response[:200]})
            raise InvalidResponseFormat()

    def process_request(
        self,
        request: ChatRequest,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        """
        Process chat request and generate LLM response.
        Uses retry logic with timeout and fallback for network errors.
        Uses Redis cache to store/retrieve responses for duplicate requests.

        Args:
            request: Validated ChatRequest from API layer
            temperature: Temperature for generation (from settings if None)
            max_output_tokens: Maximum output tokens
            system_prompt: Custom system prompt (uses default from settings if None)

        Returns:
            ChatResponse with products and optional steps
        """
        if temperature is None:
            temperature = self.settings.deepseek_temperature
        
        if max_output_tokens is None:
            max_output_tokens = self.settings.deepseek_max_output_tokens

        cache_ttl = self.settings.deepseek_cache_ttl

        logger.info("Processing chat request", extra={
            "event": "REQUEST",
            "dish": request.dish,
            "people": request.people,
            "use_steps": request.use_steps,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        })

        cache_key = self._generate_cache_key(request, temperature, max_output_tokens, system_prompt, self.settings.yandex_cloud_model)

        cached_response = self.cache.get(cache_key)
        if cached_response:
            logger.info("Cache hit", extra={"event": "CACHE_HIT", "cache_key": cache_key})
            return ChatResponse(**cached_response)

        logger.info("Cache miss", extra={"event": "CACHE_MISS", "cache_key": cache_key})

        max_retries = 3
        wait_times = [1, 3]

        for attempt in range(max_retries):
            try:
                logger.info("Sending prompt to LLM", extra={
                    "event": "PROMPT",
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                    "attempt": attempt + 1,
                })
                input_text = f"Блюдо: {request.dish}. Количество персон: {request.people}."
                if request.use_steps:
                    input_text += f" Пошаговый рецепт."
                llm_response = self.client.generate(
                    input_text=input_text,
                    temperature=temperature,
                    instructions=system_prompt,
                    max_output_tokens=max_output_tokens,
                )

                logger.info("Received LLM response", extra={
                    "event": "LLM_RESPONSE",
                    "response_preview": llm_response[:200],
                })

                parsed = self._parse_llm_response(llm_response, request.use_steps)

                response = ChatResponse(
                    products=parsed.get('products', []),
                    steps=parsed.get('steps'),
                )

                self.cache.set(
                    cache_key,
                    response.model_dump(),
                    ttl=cache_ttl,
                )

                logger.info("Chat request completed", extra={
                    "event": "RESPONSE",
                    "products_count": len(response.products),
                    "steps_count": len(response.steps) if response.steps else 0,
                })

                return response

            except Exception as e:
                logger.error("LLM call failed", extra={
                    "event": "ERROR",
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "error": str(e),
                })

                if not isinstance(e, (openai.APITimeoutError, openai.RateLimitError, openai.InternalServerError)):
                    logger.error("LLM Service Error", extra={"event": "LLM Service Error"})
                    raise

                if attempt < max_retries - 1:
                    wait_time = wait_times[attempt]
                    logger.warning("Retrying after delay", extra={
                        "event": "RETRY",
                        "wait_seconds": wait_time,
                    })
                    time.sleep(wait_time)
                else:
                    logger.warning("LLM processing failed after all retries", extra={
                        "event": "FAILED",
                        "max_retries": max_retries,
                        "error": str(e),
                    })
                    raise


# Default instance for convenience
chat_service = ChatService()
