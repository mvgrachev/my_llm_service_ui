from api.models import ChatRequest, ChatResponse
from llm import deepseek_client
from config import settings
from cache import cache
from typing import Optional
import json
import hashlib
import time
import logging
import os
import socket


logger = logging.getLogger('llm_service.chat')


class ChatService:
    """Service for handling chat interactions with LLM."""

    def __init__(self, client=None, settings=None, cache_client=None):
        self.client = client or deepseek_client
        self.settings = settings or settings
        self.cache = cache_client or cache

    def _generate_cache_key(self, request: ChatRequest, temperature: float, max_output_tokens: int) -> str:
        key_data = {
            "dish": request.dish,
            "people": request.people,
            "use_steps": request.use_steps,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return f"chat:{hashlib.md5(key_str.encode()).hexdigest()}"

    def _check_network(self, timeout: Optional[int] = None) -> bool:
        timeout = timeout if timeout is not None else int(os.getenv("NETWORK_CHECK_TIMEOUT", "5"))
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            return True
        except socket.error:
            return False

    def _parse_llm_response(self, response: str) -> dict:
        """Parse LLM response and extract products and steps fields."""
        try:
            data = json.loads(response)
            result = {}

            for key in ['products', 'продукты', 'ингредиенты', 'ingredients']:
                if key in data:
                    result['products'] = data[key]
                    break

            for key in ['steps', 'шаги', 'instructions', 'instruction']:
                if key in data:
                    result['steps'] = data[key]
                    break

            return result
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response as JSON: {response[:200]}...")
            return {}

    def _create_fallback_response(self, error_message: str) -> ChatResponse:
        return ChatResponse(
            products=[],
            steps=None,
        )

    def _create_error_response(self, error_message: str) -> ChatResponse:
        raise UnauthorizedError(error_message)

    def _is_unauthorized_error(self, error_str: str) -> bool:
        """Check if the error is due to an invalid/unauthenticated API key."""
        return 'unauthenticated' in error_str or 'unauthorized' in error_str or 'invalid api key' in error_str

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
            temperature: Temperature for generation (from env DEEPSEEK_TEMPERATURE if None)
            max_output_tokens: Maximum output tokens
            system_prompt: Custom system prompt (uses default if None)

        Returns:
            ChatResponse with products and optional steps
        """
        if temperature is None:
            temperature = self.settings.deepseek_temperature if self.settings else float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3"))

        cache_ttl = self.settings.deepseek_cache_ttl if self.settings else int(os.getenv("DEEPSEEK_CACHE_TTL", "600"))

        logger.info(
            f"[REQUEST] Time: {time.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"Dish: {request.dish}, People: {request.people}, Use steps: {request.use_steps}"
        )

        cache_key = self._generate_cache_key(request, temperature, max_output_tokens)

        cached_response = self.cache.get(cache_key)
        if cached_response:
            logger.info(f"[CACHE HIT] Key: {cache_key}, Response: {json.dumps(cached_response)}")
            return ChatResponse(**cached_response)

        logger.info(f"[CACHE MISS] Key: {cache_key}")

        max_retries = 3
        wait_times = [1, 3, 5]

        for attempt in range(max_retries + 1):
            try:
                logger.info(f"[PROMPT] Temperature: {temperature}, Max tokens: {max_output_tokens}")
                input_text = f"Блюдо: {request.dish}. Количество персон: {request.people}."
                if request.use_steps:
                    input_text += f" Пошаговый рецепт."
                llm_response = self.client.generate(
                    input_text=input_text,
                    temperature=temperature,
                    instructions=system_prompt,
                    max_output_tokens=max_output_tokens,
                )

                logger.info(f"[LLM RESPONSE] Raw response: {llm_response[:200]}...")

                parsed = self._parse_llm_response(llm_response)

                response = ChatResponse(
                    products=parsed.get('products', []),
                    steps=parsed.get('steps'),
                )

                self.cache.set(
                    cache_key,
                    response.model_dump(),
                    ttl=cache_ttl,
                )

                logger.info(
                    f"[RESPONSE] Products: {len(response.products)}, "
                    f"Steps: {len(response.steps) if response.steps else 0}, "
                    f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                return response

            except Exception as e:
                error_str = str(e).lower()
                logger.error(f"[ERROR] Attempt {attempt + 1}/{max_retries}: {error_str}")

                # If the auth error is detected, break immediately — no point retrying
                if self._is_unauthorized_error(error_str):
                    logger.error("[AUTH FAILED] Invalid or expired API key. Stopping retries.")
                    return self._create_error_response(
                        "Ошибка авторизации: недействительный или истёкший API-ключ. Пожалуйста, проверьте настройки."
                    )

                is_network_error = (
                    'network' in error_str
                    or 'connection' in error_str
                    or 'timeout' in error_str
                    or 'refused' in error_str
                )

                if is_network_error and not self._check_network():
                    fallback_response = self._create_fallback_response(f"Network error: {str(e)}")
                    self.cache.set(
                        cache_key,
                        fallback_response.model_dump(),
                        ttl=60,
                    )
                    return fallback_response

                if attempt < max_retries:
                    wait_time = wait_times[attempt]
                    logger.warning(f"[RETRY] Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    fallback_response = self._create_fallback_response(f"Try out: {str(e)}")
                    logger.warning(f"[FAILED] LLM processing error after {max_retries} attempts: {str(e)}")
                    return fallback_response


# Default instance for convenience
chat_service = ChatService()
