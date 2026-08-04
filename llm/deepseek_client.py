"""DeepSeek client for Yandex Cloud."""
from dotenv import load_dotenv

load_dotenv()

import openai
import logging
from typing import Optional
from config import settings

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
            folder_id: Yandex Cloud folder ID (from settings.yandex_cloud_folder)
            api_key: Yandex Cloud API key (from settings.yandex_cloud_api_key)
            model: Model name (from settings.yandex_cloud_model)
            prompt: System prompt for recipe generation (from settings.system_prompt or DEFAULT_PROMPT)
            timeout: Request timeout in seconds (from settings.deepseek_timeout, default 30)
        """
        self.base_url = settings.yandex_cloud_base_url
        self.folder_id = folder_id or settings.yandex_cloud_folder
        self.api_key = api_key or settings.yandex_cloud_api_key
        self.model = model or settings.yandex_cloud_model
        self.prompt = prompt or settings.system_prompt or DEFAULT_PROMPT
        self.timeout = timeout if timeout is not None else settings.deepseek_timeout

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
            temperature: Temperature for generation (from settings.deepseek_temperature if None)
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
            temperature = settings.deepseek_temperature

        logger.info(f"[DEEPSEEK] Generating response for input: {input_text[:100]}...")
        logger.info(f"[DEEPSEEK] Prompt: {prompt_text[:200]}...")

        try:
            # Pass timeout directly to the OpenAI client constructor.
            # The SDK (v1+) uses httpx under the hood and enforces this
            # timeout at the HTTP level — the actual network request is
            # cancelled when the time expires, unlike the old threading
            # approach which only interrupted the waiting thread.
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                project=self.folder_id,
                timeout=self.timeout,
            )

            response = client.responses.create(
                model=f"gpt://{self.folder_id}/{self.model}",
                temperature=temperature,
                instructions=prompt_text,
                input=input_text,
                max_output_tokens=max_output_tokens,
            )

            result = response.output_text
            logger.info(f"[DEEPSEEK] Response received: {result[:200]}...")
            return result
        except openai.APITimeoutError as e:
            logger.error(f"[DEEPSEEK] Request timed out after {self.timeout} seconds: {str(e)}")
            raise TimeoutError(f"LLM call timed out after {self.timeout} seconds") from e
        except openai.APIConnectionError as e:
            logger.error(f"[DEEPSEEK] Connection error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[DEEPSEEK] Error during generation: {str(e)}")
            raise


# Default instance for convenience
deepseek_client = DeepSeekClient()
