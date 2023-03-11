import logging
from asyncio import AbstractEventLoop, Future, get_event_loop

from aiogram import Bot, Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.executor import start_polling, start_webhook

from randomall_tg_bot.config import (
    DEBUG,
    MQ_URL,
    TELEGRAM_API_TOKEN,
    TELEGRAM_WEBHOOK_HOST,
    TELEGRAM_WEBHOOK_PORT,
    TELEGRAM_WEBHOOK_URL,
)
from randomall_tg_bot.messages import COMMAND_CUSTOM, COMMAND_GENERAL, Response
from randomall_tg_bot.mq import create_mq
from randomall_tg_bot.router import Router


async def on_startup(dp: Dispatcher) -> None:
    logging.debug("Startup")
    if not DEBUG:
        await dp.bot.set_webhook(TELEGRAM_WEBHOOK_URL)


async def on_shutdown(dp: Dispatcher) -> None:
    logging.debug("Shutdown")
    if not DEBUG:
        await dp.bot.delete_webhook()


def start_bot(
    loop: AbstractEventLoop,
    dp: Dispatcher,
) -> None:
    if DEBUG:
        start_polling(
            dp,
            loop=loop,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
        )
    else:
        start_webhook(
            dp,
            loop=loop,
            webhook_path=TELEGRAM_WEBHOOK_URL,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
            host=TELEGRAM_WEBHOOK_HOST,
            port=TELEGRAM_WEBHOOK_PORT,
        )


def start_service(loop: AbstractEventLoop):
    level = logging.DEBUG if DEBUG else logging.INFO
    logging.basicConfig(level=level)
    uuids_map: dict[str, Future[Response]] = {}
    mq = loop.run_until_complete(create_mq(loop, MQ_URL, uuids_map))
    bot = Bot(TELEGRAM_API_TOKEN, parse_mode="MarkdownV2")
    dp = Dispatcher(bot)
    if DEBUG:
        dp.middleware.setup(LoggingMiddleware())

    router = Router(bot, mq, uuids_map)
    dp.register_message_handler(router.help, commands=["start", "help"])
    dp.register_message_handler(
        dp.async_task(router.general), commands=[COMMAND_GENERAL, "g"]
    )
    dp.register_message_handler(
        dp.async_task(router.custom), commands=[COMMAND_CUSTOM, "c"]
    )
    dp.register_callback_query_handler(dp.async_task(router.callback))

    # TODO: handle reconnect
    loop.create_task(mq.recv())

    start_bot(loop, dp)


if __name__ == "__main__":
    loop = get_event_loop()
    start_service(loop)
