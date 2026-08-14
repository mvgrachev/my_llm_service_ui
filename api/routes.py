"""Chat routing and endpoints."""

from fastapi import APIRouter, HTTPException
import openai
from api.models import ChatRequest, ChatResponse
from services import chat_service
from services.chat import EmptyResponse, InvalidResponseFormat
from config.logging_config import get_logger

logger = get_logger('llm_service.routes')

router = APIRouter(prefix="/chat", tags=["chat"])


def _is_auth_error(error: BaseException) -> bool:
    """Check if the error is an authentication/API-key failure."""
    return isinstance(error, openai.AuthenticationError)


@router.post("", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Process chat message and return response from LLM.

    Args:
        request: ChatRequest with message field

    Returns:
        ChatResponse with products and steps,
        or exceptions
    """
    try:
        logger.info("Chat request received", extra={
            "event": "chat.request",
            "source": "routes",
            "dish": request.dish,
            "people": request.people,
            "use_steps": request.use_steps,
        })
        response = chat_service.process_request(request)
        logger.info("Chat request completed", extra={
            "event": "chat.response",
            "source": "routes",
            "products_count": len(response.products),
            "steps_count": len(response.steps) if response.steps else 0,
        })
        return response
    except EmptyResponse:
        logger.warning("Empty response from LLM", extra={
            "event": "chat.empty_response",
            "source": "routes",
            "dish": request.dish,
        })
        raise HTTPException(
            status_code=422,
            detail=(
                "LLM вернул пустой ответ. "
                "Попробуйте изменить запрос."
            )
        )
    except InvalidResponseFormat:
        logger.warning("Invalid response format from LLM", extra={
            "event": "chat.invalid_format",
            "source": "routes",
            "dish": request.dish,
        })
        raise HTTPException(
            status_code=502,
            detail=(
                "Не удалось обработать ответ от LLM. "
                "Попробуйте позже."
            )
        )
    except Exception as e:
        logger.error("Error in chat endpoint", extra={
            "event": "chat.error",
            "source": "routes",
            "error": str(e),
        })

        if isinstance(e, openai.APITimeoutError):
            raise HTTPException(
                status_code=429,
                detail=(
                    "Время ожидания ответа истекло. "
                    "Пожалуйста, попробуйте позже."
                )
            )
        elif isinstance(e, openai.APIConnectionError):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Сервис временно недоступен. "
                    "Попробуйте позже "
                    "или обратитесь в техподдержку."
                )
            )
        elif isinstance(
            e,
            (
                openai.AuthenticationError,
                openai.PermissionDeniedError
            )
        ):
            raise HTTPException(
                status_code=e.status_code,
                detail=(
                    "Ошибка авторизации: "
                    "недействительный или истёкший API-ключ. "
                    "Пожалуйста, проверьте настройки."
                )
            )
        elif isinstance(e, openai.RateLimitError):
            raise HTTPException(
                status_code=e.status_code,
                detail=(
                    "Превышена частота обращения к сервису. "
                    "Пожалуйста, попробуйте позже."
                )
            )
        elif isinstance(e, openai.InternalServerError):
            raise HTTPException(
                status_code=e.status_code,
                detail=(
                    "Ошибка LLM. "
                    "Пожалуйста, попробуйте позже."
                )
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Непредвиденная ошибка. "
                    "Попробуйте позже или обратитесь в техподдержку."
                )
            )
