from loguru import logger

from brvideo.core.config import settings
from brvideo.core import logging

logging.setup_logger(level="INFO")


async def run() -> None:
    from brvideo.core import managers, models

    await models.init()
    await managers.initialize()

    from brvideo.bot.services.bot import BotService, BotServiceConfig

    botservice = BotService(service_config=BotServiceConfig(token=settings.TOKEN))

    await botservice.run()

    await models.close()
    await botservice.bot.session.close()
    await managers.close()

    logger.warning("Bot stopped")
