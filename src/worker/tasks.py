import asyncio

import dramatiq

from src.core.logger import logger
from src.database.session import async_session_maker
from src.services.analytics_service import AnalyticsService
from src.worker.broker import redis_broker  # noqa: F401


@dramatiq.actor
def generate_weekly_report() -> None:
    logger.info("Starting report generation...")

    async def run_task() -> None:
        async with async_session_maker() as session:
            service = AnalyticsService(session)
            data = await service.get_weekly_analysis()
            logger.info("Weekly report calculated: %s", data)

    asyncio.run(run_task())

    logger.info("Report generation completed")
