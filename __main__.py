"""Allow running the service as a module: python -m llm_service"""
import asyncio
from dotenv import load_dotenv

load_dotenv()


async def main():
    """Main application entry point"""
    import main as app_module
    app_module.logger.info("Starting LLM Service...")
    await app_module.main()


if __name__ == "__main__":
    asyncio.run(main())
