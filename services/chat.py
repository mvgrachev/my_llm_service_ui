from api.models import ChatRequest, ChatResponse
from llm import deepseek_client
from config import settings
from cache import cache
from typing import Optional
import json
import hashlib
import time
import logging
import socket
import openai


logger = logging.getLogger('llm_service.chat')


class UnauthorizedError(Exception):
    """Raised when LLM API key is invalid or expired."""


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

        cache_ttl = self.settings.deepseek_cache_ttl

        logger.info(
            f"[REQUEST] Time: {time.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"Dish: {request.dish}, People: {request.people}, Use steps: {request.use_steps}"
        )

        cache_key = self._generate_cache_key(request, temperature, max_output_tokens, system_prompt, self.settings.yandex_cloud_model)

        cached_response = self.cache.get(cache_key)
        if cached_response:
            logger.info(f"[CACHE HIT] Key: {cache_key}, Response: {json.dumps(cached_response)}")
            return ChatResponse(**cached_response)

        logger.info(f"[CACHE MISS] Key: {cache_key}")

        max_retries = 3
        wait_times = [1, 3]

        for attempt in range(max_retries):
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
                logger.error(f"[ERROR] Attempt {attempt + 1}/{max_retries}: {e}")
                
                is_network_error = (
                    isinstance(e, (openai.APIConnectionError))
                )

                if is_network_error:
                    fallback_response = self._create_fallback_response(f"Network error: {str(e)}")
                    logger.error("[NETWORK ERROR] Invalid or expired API key. Stopping retries.")
                    return fallback_response
                
                is_authentication_error = (
                    isinstance(e, (openai.AuthenticationError))
                )

                # If the auth error is detected, break immediately — no point retrying
                if is_authentication_error:
                    logger.error("[AUTH FAILED] Invalid or expired API key. Stopping retries.")
                    return self._create_error_response(
                        "Ошибка авторизации: недействительный или истёкший API-ключ. Пожалуйста, проверьте настройки."
                    )

                if attempt < max_retries - 1:
                    wait_time = wait_times[attempt]
                    logger.warning(f"[RETRY] Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    fallback_response = self._create_fallback_response(f"Try out: {str(e)}")
                    logger.warning(f"[FAILED] LLM processing error after {max_retries} attempts: {str(e)}")
                    return fallback_response


# Default instance for convenience
chat_service = ChatService()
