"""Unit tests for chat endpoint and service."""
import pytest
import socket
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app
from api.models import ChatRequest, ChatResponse
from services.chat import ChatService
from cache.redis_client import CacheClient


class TestChatRequest:
    """Tests for ChatRequest model validation."""

    def test_valid_request(self):
        """Test creation of a valid request."""
        request = ChatRequest(dish="Паста Карбонара", people=2)
        assert request.dish == "Паста Карбонара"
        assert request.people == 2
        assert request.use_steps is None

    def test_valid_request_with_steps(self):
        """Test creation of a valid request with steps."""
        request = ChatRequest(dish="Борщ", people=4, use_steps=True)
        assert request.dish == "Борщ"
        assert request.people == 4
        assert request.use_steps is True

    def test_empty_dish_rejected(self):
        """Test that empty dish is rejected."""
        with pytest.raises(Exception):
            ChatRequest(dish="", people=2)

    def test_whitespace_dish_rejected(self):
        """Test that whitespace-only dish is rejected."""
        with pytest.raises(Exception):
            ChatRequest(dish="   ", people=2)

    def test_dish_stripped(self):
        """Test that dish is stripped of whitespace."""
        request = ChatRequest(dish="  Паста  ", people=2)
        assert request.dish == "Паста"

    def test_people_min(self):
        """Test minimum people value."""
        request = ChatRequest(dish="Салат", people=1)
        assert request.people == 1

    def test_people_max(self):
        """Test maximum people value."""
        request = ChatRequest(dish="Салат", people=1000)
        assert request.people == 1000

    def test_people_too_low(self):
        """Test that people < 1 is rejected."""
        with pytest.raises(Exception):
            ChatRequest(dish="Салат", people=0)

    def test_people_too_high(self):
        """Test that people > 1000 is rejected."""
        with pytest.raises(Exception):
            ChatRequest(dish="Салат", people=1001)

    def test_missing_dish_rejected(self):
        """Test that missing dish is rejected."""
        with pytest.raises(Exception):
            ChatRequest(people=2)

    def test_missing_people_rejected(self):
        """Test that missing people is rejected."""
        with pytest.raises(Exception):
            ChatRequest(dish="Салат")


class TestChatResponse:
    """Tests for ChatResponse model."""

    def test_valid_response(self):
        """Test creation of a valid response."""
        response = ChatResponse(products=["мука", "яйца"])
        assert response.products == ["мука", "яйца"]
        assert response.steps is None

    def test_response_with_steps(self):
        """Test creation of a response with steps."""
        response = ChatResponse(
            products=["мука", "яйца"],
            steps=["смешать", "выпечь"]
        )
        assert response.products == ["мука", "яйца"]
        assert response.steps == ["смешать", "выпечь"]

    def test_response_with_empty_products(self):
        """Test that empty products list is valid."""
        response = ChatResponse(products=[])
        assert response.products == []

    def test_model_dump(self):
        """Test model serialization."""
        response = ChatResponse(
            products=["мука"],
            steps=["смешать"]
        )
        data = response.model_dump()
        assert data['products'] == ["мука"]
        assert data['steps'] == ["смешать"]


class TestChatService:
    """Tests for ChatService class."""

    def test_init_default(self):
        """Test ChatService initialization with defaults."""
        service = ChatService()
        assert service.client is not None
        assert service.cache is not None


    def test_init_custom(self):
        """Test ChatService initialization with custom dependencies."""
        mock_client = Mock()
        mock_settings = Mock()
        mock_cache = Mock()

        service = ChatService(client=mock_client, settings_obj=mock_settings, cache_client=mock_cache)
        assert service.client == mock_client
        assert service.settings == mock_settings
        assert service.cache == mock_cache

    def test_generate_cache_key(self):
        """Test cache key generation."""
        service = ChatService()
        request = ChatRequest(dish="Паста", people=2, use_steps=False)

        key = service._generate_cache_key(request, temperature=0.3, max_output_tokens=1500, system_prompt="System prompt", model="Model")

        assert key.startswith("chat:")
        assert len(key) == 37  # "chat:" + 32 hex chars

    def test_generate_cache_key_different_dishes(self):
        """Test that different dishes produce different keys."""
        service = ChatService()
        request1 = ChatRequest(dish="Паста", people=2)
        request2 = ChatRequest(dish="Борщ", people=2)

        key1 = service._generate_cache_key(request1, 0.3, 1500, "System prompt", "Model")
        key2 = service._generate_cache_key(request2, 0.3, 1500, "System prompt", "Model")

        assert key1 != key2

    def test_generate_cache_key_different_people(self):
        """Test that different people count produces different keys."""
        service = ChatService()
        request1 = ChatRequest(dish="Паста", people=2)
        request2 = ChatRequest(dish="Паста", people=4)

        key1 = service._generate_cache_key(request1, 0.3, 1500, "System prompt", "Model")
        key2 = service._generate_cache_key(request2, 0.3, 1500, "System prompt", "Model")

        assert key1 != key2

    def test_generate_cache_key_same_params(self):
        """Test that same params produce same keys."""
        service = ChatService()
        request = ChatRequest(dish="Паста", people=2, use_steps=True)

        key1 = service._generate_cache_key(request, 0.3, 1500, "System prompt", "Model")
        key2 = service._generate_cache_key(request, 0.3, 1500, "System prompt", "Model")

        assert key1 == key2

    def test_parse_llm_response_json(self):
        """Test parsing LLM response with products and steps."""
        service = ChatService()
        response = '{"products": ["мука", "яйца"], "steps": ["смешать", "выпечь"]}'
        use_steps = True

        parsed = service._parse_llm_response(response,use_steps)

        assert parsed['products'] == ["мука", "яйца"]
        assert parsed['steps'] == ["смешать", "выпечь"]

    def test_parse_llm_response_incorrect_json(self):
        """Test parsing LLM response with products and steps."""
        service = ChatService()
        response = 'Dscription: test test test {"products": ["мука", "яйца"], "steps": ["смешать", "выпечь"]} description test test test'
        use_steps = True

        parsed = service._parse_llm_response(response,use_steps)

        assert parsed['products'] == ["мука", "яйца"]
        assert parsed['steps'] == ["смешать", "выпечь"]

    def test_parse_llm_response_products_only(self):
        """Test parsing LLM response with only products."""
        service = ChatService()
        response = '{"ingredients": ["мука", "яйца"]}'
        use_steps = False

        parsed = service._parse_llm_response(response,use_steps)

        assert parsed['products'] == ["мука", "яйца"]
        assert 'steps' not in parsed

    def test_parse_llm_response_russian_keys(self):
        """Test parsing LLM response with Russian keys."""
        service = ChatService()
        response = '{"продукты": ["хлеб", "масло"], "шаги": ["нарезать", "поджарить"]}'
        use_steps = True

        parsed = service._parse_llm_response(response,use_steps)

        assert parsed['products'] == ["хлеб", "масло"]
        assert parsed['steps'] == ["нарезать", "поджарить"]

    def test_process_request_cache_hit(self):
        """Test processing request with cache hit."""
        service = ChatService()
        request = ChatRequest(dish="Паста", people=2, use_steps=True)

        cached_data = {"products": ["мука", "яйца"], "steps": ["смешать", "выпечь"]}

        with patch.object(service.cache, 'get', return_value=cached_data) as mock_get:
            response = service.process_request(request)

            assert isinstance(response, ChatResponse)
            assert response.products == ["мука", "яйца"]
            assert response.steps == ["смешать", "выпечь"]
            mock_get.assert_called_once()


class TestChatEndpoint:
    """Tests for chat endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app, raise_server_exceptions=True)

    def test_chat_endpoint_success(self, client):
        """Test successful chat endpoint request."""
        request_data = {"dish": "Паста Карбонара", "people": 2}

        mock_response = ChatResponse(
            products=["мука", "яйца", "бекон"],
            steps=["отварить пасту", "обжарить бекон", "смешать"],
        )

        with patch('services.chat.chat_service.process_request', return_value=mock_response):
            response = client.post("/chat", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data['products'] == ["мука", "яйца", "бекон"]
            assert data['steps'] == ["отварить пасту", "обжарить бекон", "смешать"]

    def test_chat_endpoint_success_with_steps_false(self, client):
        """Test chat endpoint with steps disabled."""
        request_data = {"dish": "Салат", "people": 1, "use_steps": False}

        mock_response = ChatResponse(
            products=["огурцы", "помидоры"],
            steps=None,
        )

        with patch('services.chat.chat_service.process_request', return_value=mock_response):
            response = client.post("/chat", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data['products'] == ["огурцы", "помидоры"]
            assert data['steps'] is None

    def test_chat_endpoint_empty_dish(self, client):
        """Test chat endpoint with empty dish."""
        request_data = {"dish": "", "people": 2}

        response = client.post("/chat", json=request_data)

        assert response.status_code == 422

    def test_chat_endpoint_missing_dish(self, client):
        """Test chat endpoint with missing dish."""
        request_data = {"people": 2}

        response = client.post("/chat", json=request_data)

        assert response.status_code == 422

    def test_chat_endpoint_missing_people(self, client):
        """Test chat endpoint with missing people."""
        request_data = {"dish": "Салат"}

        response = client.post("/chat", json=request_data)

        assert response.status_code == 422

    def test_chat_endpoint_people_too_low(self, client):
        """Test chat endpoint with people < 1."""
        request_data = {"dish": "Салат", "people": 0}

        response = client.post("/chat", json=request_data)

        assert response.status_code == 422

    def test_chat_endpoint_people_too_high(self, client):
        """Test chat endpoint with people > 1000."""
        request_data = {"dish": "Салат", "people": 1001}

        response = client.post("/chat", json=request_data)

        assert response.status_code == 422

    def test_chat_endpoint_llm_error(self, client):
        """Test chat endpoint with LLM error."""
        request_data = {"dish": "Паста", "people": 2}

        with patch('services.chat.chat_service.process_request', side_effect=Exception("LLM Error")):
            response = client.post("/chat", json=request_data)

            assert response.status_code == 500
            data = response.json()
            assert "Непредвиденная ошибка. Попробуйте позже или обратитесь в техподдержку." in data['detail']

    def test_chat_endpoint_timeout_error(self, client):
        """Test chat endpoint with openai.APITimeoutError."""
        import openai
        request_data = {"dish": "Паста", "people": 2}

        with patch('services.chat.chat_service.process_request', side_effect=openai.APITimeoutError("Request timed out")):
            response = client.post("/chat", json=request_data)

            assert response.status_code == 429
            data = response.json()
            assert "Время ожидания ответа истекло" in data['detail']
            
    def test_chat_endpoint_connection_error(self, client):
        """Test chat endpoint with openai.APIConnectionError."""
        import openai
        request_data = {"dish": "Паста", "people": 2}
        mock_request = type('Request', (), {'url': 'http://test'})()
        with patch('services.chat.chat_service.process_request', side_effect=openai.APIConnectionError(request=mock_request)):
            response = client.post("/chat", json=request_data)
            
            assert response.status_code == 503
            data = response.json()
            assert "Сервис временно недоступен" in data['detail']

    def test_chat_endpoint_authentication_error(self, client):
        """Test chat endpoint with openai.AuthenticationError (AuthenticationError)."""
        import openai
        request_data = {"dish": "Паста", "people": 2}
        mock_response = Mock()
        mock_response.request = Mock()
        mock_response.status_code = 401
        with patch('services.chat.chat_service.process_request', side_effect=openai.AuthenticationError("Invalid API key", response=mock_response, body=None)):
            response = client.post("/chat", json=request_data)

            assert response.status_code == 401
            data = response.json()
            assert "Ошибка авторизации" in data['detail']
    
    def test_chat_endpoint_permission_denied_error(self, client):
        """Test chat endpoint with openai.PermissionDeniedError (PermissionDeniedError)."""
        import openai
        request_data = {"dish": "Паста", "people": 2}
        mock_response = Mock()
        mock_response.request = Mock()
        mock_response.status_code = 401
        with patch('services.chat.chat_service.process_request', side_effect=openai.PermissionDeniedError("Invalid API key", response=mock_response, body=None)):
            response = client.post("/chat", json=request_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "Ошибка авторизации" in data['detail']

    def test_chat_endpoint_rate_limit_error(self, client):
        """Test chat endpoint with openai.RateLimitError."""
        import openai
        request_data = {"dish": "Паста", "people": 2}
        mock_response = Mock()
        mock_response.request = Mock()
        mock_response.status_code = 429
        with patch('services.chat.chat_service.process_request', side_effect=openai.RateLimitError("Rate limit exceeded", response=mock_response, body=None)):
            response = client.post("/chat", json=request_data)
        
        assert response.status_code == 429
        data = response.json()
        assert "Превышена частота обращения к сервису" in data['detail']

    def test_chat_endpoint_internal_server_error(self, client):
        """Test chat endpoint with openai.InternalServerError."""
        import openai
        request_data = {"dish": "Паста", "people": 2}
        mock_response = Mock()
        mock_response.request = Mock()
        mock_response.status_code = 500
        with patch('services.chat.chat_service.process_request', side_effect=openai.InternalServerError("Internal server error", response=mock_response, body=None)):
            response = client.post("/chat", json=request_data)

        assert response.status_code == 500
        data = response.json()
        assert "Ошибка LLM" in data['detail']

class TestCacheClient:
    """Tests for CacheClient class."""

    def test_get_nonexistent_key(self):
        """Test getting nonexistent key."""
        cache = CacheClient()

        result = cache.get("nonexistent_key")

        assert result is None

    def test_set_and_get(self):
        """Test setting and getting value."""
        cache = CacheClient()

        cache.set("test_key", {"products": ["мука"], "steps": ["смешать"]}, ttl=60)
        result = cache.get("test_key")

        assert result is not None
        assert result['products'] == ["мука"]
        assert result['steps'] == ["смешать"]

    def test_exists_key(self):
        """Test checking if key exists."""
        cache = CacheClient()

        cache.set("exists_key", {"test": "value"})
        result = cache.exists("exists_key")

        assert result is True

    def test_exists_nonexistent_key(self):
        """Test checking if nonexistent key exists."""
        cache = CacheClient()

        result = cache.exists("nonexistent_key")

        assert result is False


class TestEmptyResponse:
    """Tests for EmptyResponse exception."""

    def test_exception_is_raised(self):
        """Test that EmptyResponse is a subclass of Exception."""
        from services.chat import EmptyResponse

        assert issubclass(EmptyResponse, Exception)
        exc = EmptyResponse()
        assert isinstance(exc, Exception)

    def test_exception_message(self):
        """Test EmptyResponse can carry a message."""
        from services.chat import EmptyResponse

        exc = EmptyResponse("No products found")
        assert str(exc) == "No products found"

    def test_parse_llm_response_missing_products_raises_empty_response(self):
        """Test that missing 'products' key raises EmptyResponse."""
        from services.chat import ChatService, EmptyResponse

        service = ChatService()
        response = '{"steps": ["смешать", "выпечь"]}'
        use_steps = False

        with pytest.raises(EmptyResponse):
            service._parse_llm_response(response, use_steps)

    def test_parse_llm_response_empty_products_raises_empty_response(self):
        """Test that empty string 'products' raises EmptyResponse."""
        from services.chat import ChatService, EmptyResponse

        service = ChatService()
        response = '{"products": ""}'
        use_steps = False

        with pytest.raises(EmptyResponse):
            service._parse_llm_response(response, use_steps)

    def test_parse_llm_response_products_whitespace_only_raises_empty_response(self):
        """Test that whitespace-only 'products' raises EmptyResponse."""
        from services.chat import ChatService, EmptyResponse
        service = ChatService()
        response = '{"products": "   "}'
        use_steps = False
        # products is whitespace only, so EmptyResponse should be raised
        with pytest.raises(EmptyResponse):
            service._parse_llm_response(response, use_steps)
    
    def test_parse_llm_response_empty_ingredients_raises_empty_response(self):
        """Test that empty 'ingredients' key raises EmptyResponse."""
        from services.chat import ChatService, EmptyResponse

        service = ChatService()
        response = '{"ingredients": ""}'
        use_steps = False

        with pytest.raises(EmptyResponse):
            service._parse_llm_response(response, use_steps)

    def test_parse_llm_response_empty_products_rus_raises_empty_response(self):
        """Test that empty 'продукты' key raises EmptyResponse."""
        from services.chat import ChatService, EmptyResponse

        service = ChatService()
        response = '{"продукты": ""}'
        use_steps = False

        with pytest.raises(EmptyResponse):
            service._parse_llm_response(response, use_steps)


class TestInvalidResponseFormat:
    """Tests for InvalidResponseFormat exception."""

    def test_exception_is_raised(self):
        """Test that InvalidResponseFormat is a subclass of Exception."""
        from services.chat import InvalidResponseFormat

        assert issubclass(InvalidResponseFormat, Exception)
        exc = InvalidResponseFormat()
        assert isinstance(exc, Exception)

    def test_exception_message(self):
        """Test InvalidResponseFormat can carry a message."""
        from services.chat import InvalidResponseFormat

        exc = InvalidResponseFormat("Invalid JSON format")
        assert str(exc) == "Invalid JSON format"

    def test_parse_llm_response_completely_invalid_json_raises(self):
        """Test that completely invalid JSON raises InvalidResponseFormat."""
        from services.chat import ChatService, InvalidResponseFormat

        service = ChatService()
        response = 'not json at all'
        use_steps = False

        with pytest.raises(InvalidResponseFormat):
            service._parse_llm_response(response, use_steps)

    def test_parse_llm_response_malformed_json_raises(self):
        """Test that malformed JSON raises InvalidResponseFormat."""
        from services.chat import ChatService, InvalidResponseFormat

        service = ChatService()
        response = '{"products": "мука", "steps": ["смешать"}'  # missing closing braces
        use_steps = True

        with pytest.raises(InvalidResponseFormat):
            service._parse_llm_response(response, use_steps)

    def test_parse_llm_response_no_braces_invalid_json_raises(self):
        """Test that text with no braces that is not valid JSON raises InvalidResponseFormat."""
        from services.chat import ChatService, InvalidResponseFormat

        service = ChatService()
        response = 'Сегодня отличная погода, пойдем гулять'
        use_steps = False

        with pytest.raises(InvalidResponseFormat):
            service._parse_llm_response(response, use_steps)