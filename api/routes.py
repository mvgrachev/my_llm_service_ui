"""Chat routing and endpoints."""

from fastapi import APIRouter, HTTPException
from typing import Union
from api.models import ChatRequest, ChatResponse, AuthError
from services import chat_service
from services.chat import UnauthorizedError
import logging

logger = logging.getLogger('llm_service.routes')

router = APIRouter(prefix="/chat", tags=["chat"])


AUTH_ERROR_MSG = "Ошибка авторизации: недействительный или истёкший API-ключ. Пожалуйста, проверьте настройки."


def _is_auth_error(error_str: str) -> bool:
    """Check if the error is an authentication/API-key failure."""
    lower = error_str.lower()
    return any(
        marker in lower
        for marker in [
            "unauthenticated",
            "unknown api key",
            "invalid api key",
            "unauthorized",
            "api key not found",
            "api key invalid",
            "invalid_api_key",
            "unauthorized_error",
        ]
    )


@router.post("", response_model=Union[ChatResponse, AuthError])
async def chat_endpoint(request: ChatRequest):
    """
    Process chat message and return response from LLM.
    
    Args:
        request: ChatRequest with message field
        
    Returns:
        ChatResponse with products and steps, or AuthError if API key is invalid
    """
    try:
        response = chat_service.process_request(request)
        return response
    except UnauthorizedError:
        logger.error(f"Authentication error in chat endpoint: {AUTH_ERROR_MSG}")
        return AuthError(message=AUTH_ERROR_MSG)
    except Exception as e:
        error_str = str(e)
        logger.error(f"Error in chat endpoint: {error_str}")

        if _is_auth_error(error_str):
            return AuthError(message=AUTH_ERROR_MSG)

        raise HTTPException(status_code=500, detail=f"Internal server error: {error_str}")
