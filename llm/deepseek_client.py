"""DeepSeek client for Yandex Cloud."""
import os
import openai
import threading
import queue
import logging
from typing import Optional

logger = logging.getLogger('llm_service.deepseek')

# Default prompt for recipe generation
DEFAULT_PROMPT = (
    "Пользователь пишет блюдо, количество персон и опционально указывает нужны ли в ответе шаги приготовления."
    "В результате получаем список продуктов с указанием веса в граммах и опционально шаги приготовления (не более 5)."
    "\n\nФормат ответа: JSON. "
    "Обязательные поля: products (список строк — каждый продукт отдельной строкой в массиве), "
    "steps (список строк — каждый шаг отдельной строкой в массиве, опционально). "
    "Без вступления, без лишних полей, только JSON."
    '\nПример: {"products": ["Мясо - 300 граммов","Картофель - 200 граммов"], "steps": ["Разморозить", "Пожарить"]}'
)

# Default timeout read from environment or fallback to 30
_DEFAULT_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "30"))


def with_timeout(timeout: int):
    """
    Decorator for adding timeout to LLM calls.

    Args:
        timeout: Timeout in seconds
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result_queue = queue.Queue()
            exception_queue = queue.Queue()

            def target():
                try:
                    result = func(*args, **kwargs)
                    result_queue.put(result)
                except Exception as e:
                    exception_queue.put(e)

            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            thread.join(timeout=timeout)

            if thread.is_alive():
                raise TimeoutError(f"LLM call timed out after {timeout} seconds")

            if not exception_queue.empty():
                raise exception_queue.get()

            return result_queue.get()

        return wrapper
    return decorator


class DeepSeekClient:
    """Client for DeepSeek model on Yandex Cloud."""

    def __init__(
        self,
        folder_id: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """
        Initialize DeepSeek client.

        Args:
            folder_id: Yandex Cloud folder ID (from env YANDEX_CLOUD_FOLDER)
            api_key: Yandex Cloud API key (from env YANDEX_CLOUD_API_KEY)
            model: Model name (from env YANDEX_CLOUD_MODEL)
            prompt: System prompt for recipe generation (from env PROMPT or DEFAULT_PROMPT)
            timeout: Request timeout in seconds (from env DEEPSEEK_TIMEOUT, default 30)
        """
        self.base_url = os.getenv("YANDEX_CLOUD_BASE_URL")
        self.folder_id = folder_id or os.getenv("YANDEX_CLOUD_FOLDER")
        self.api_key = api_key or os.getenv("YANDEX_CLOUD_API_KEY")
        self.model = model or os.getenv("YANDEX_CLOUD_MODEL", "deepseek-v4-flash/latest")
        self.prompt = prompt or os.getenv("PROMPT", DEFAULT_PROMPT)
        self.timeout = timeout if timeout is not None else _DEFAULT_TIMEOUT

        if not self.folder_id:
            raise ValueError("YANDEX_CLOUD_FOLDER environment variable is required")
        if not self.api_key:
            raise ValueError("YANDEX_CLOUD_API_KEY environment variable is required")

    def generate(
        self,
        input_text: str,
        temperature: Optional[float] = None,
        instructions: Optional[str] = None,
        max_output_tokens: Optional[int] = None
    ) -> str:
        """
        Generate response from DeepSeek model with timeout.

        Args:
            input_text: Input text for the model
            temperature: Temperature for generation (from env DEEPSEEK_TEMPERATURE if None)
            instructions: System instructions (uses self.prompt if None)
            max_output_tokens: Maximum output tokens

        Returns:
            Generated text response

        Raises:
            TimeoutError: If request takes longer than timeout
            Exception: If LLM call fails
        """
        prompt_text = instructions if instructions is not None else self.prompt

        if temperature is None:
            temperature = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3"))

        logger.info(f"[DEEPSEEK] Generating response for input: {input_text[:100]}...")
        logger.info(f"[DEEPSEEK] Prompt: {prompt_text[:200]}...")

        try:
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                project=self.folder_id
            )

            response = client.responses.create(
                model=f"gpt://{self.folder_id}/{self.model}",
                temperature=temperature,
                instructions=prompt_text,
                input=input_text,
                max_output_tokens=max_output_tokens
            )

            result = response.output_text
            logger.info(f"[DEEPSEEK] Response received: {result[:200]}...")
            return result
        except Exception as e:
            logger.error(f"[DEEPSEEK] Error during generation: {str(e)}")
            raise


# Default instance for convenience
deepseek_client = DeepSeekClient()
