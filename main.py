#!/usr/bin/env python3
"""Main entry point for the LLM Service."""
import logging
from fastapi import FastAPI
from dotenv import load_dotenv
from api import router
from config import settings
# Configure structured JSON logging (sets up root handlers once)
from config.logging_config import get_logger

# Load environment variables from .env file
load_dotenv()

logger = get_logger('llm_service')

logger.info("Application environment: %s", settings.env)

# Suppress verbose logs from external libraries
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('uvicorn').setLevel(logging.WARNING)
logging.getLogger('starlette').setLevel(logging.WARNING)

app = FastAPI(
    title="LLM Service",
    description="API service for LLM operations",
    version="1.0.0"
)

# Import and include API router
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint"""
    logger.info("Root endpoint accessed")
    return {"message": "LLM Service is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
