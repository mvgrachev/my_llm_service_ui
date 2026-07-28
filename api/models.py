"""Chat models and schemas."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    dish: str = Field(..., min_length=1, description="Блюдо")

    people: int = Field(..., ge=1, le=1000, description="Количество персон")

    use_steps: Optional[bool] = Field(default=None, description="Использовать шаги приготовления")

    @field_validator('dish')
    @classmethod
    def validate_dish(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('dish cannot be empty')
        return v.strip()


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    products: list = Field(..., description="Список продуктов")

    steps: Optional[list] = Field(default=None, description="Список шагов приготовления")


class AuthError(BaseModel):
    """Response model for authentication errors."""

    message: str = Field(..., description="Сообщение об ошибке авторизации")
