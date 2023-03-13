import logging
from asyncio import AbstractEventLoop, Future, get_event_loop

from aiogram import Bot, Dispatcher, Router as AiogramRouter, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)
from aiogram.client.session.aiohttp import AiohttpSession

from aiohttp import web
from aiohttp.web_app import Application

from randomall_tg_bot.config import (
    DEBUG,
    MQ_URL,
    TELEGRAM_API_TOKEN,
    TELEGRAM_WEBAPP_HOST,
    TELEGRAM_WEBAPP_PORT,
    TELEGRAM_WEBHOOK_HOST,
    TELEGRAM_WEBHOOK_PATH,
    TELEGRAM_WEBHOOK_URL,
)
from randomall_tg_bot.messages import COMMAND_CUSTOM, COMMAND_GENERAL, Response
from randomall_tg_bot.mq import create_mq
from randomall_tg_bot.router import Router


async def on_startup(bot: Bot) -> None:
    logging.debug("Startup")
    if not DEBUG:
        await bot.set_webhook(TELEGRAM_WEBHOOK_URL)


async def on_shutdown(bot: Bot) -> None:
    logging.debug("Shutdown")
    if not DEBUG:
        await bot.delete_webhook()


# def start_bot(
#     loop: AbstractEventLoop,
#     dp: Dispatcher,
#     bot: Bot,
# ) -> None:
#     if DEBUG:
#         start_polling(
#             dp,
#             loop=loop,
#             on_startup=on_startup,
#             on_shutdown=on_shutdown,
#             skip_updates=True,
#         )
#     else:
#         start_webhook(
#             dp,
#             loop=loop,
#             webhook_path=TELEGRAM_WEBHOOK_PATH,
#             on_startup=on_startup,
#             on_shutdown=on_shutdown,
#             skip_updates=True,
#             host=TELEGRAM_WEBAPP_HOST,
#             port=TELEGRAM_WEBAPP_PORT,
#         )


def start_service(loop: AbstractEventLoop):
    level = logging.DEBUG if DEBUG else logging.INFO
    logging.basicConfig(level=logging.DEBUG)
    uuids_map: dict[str, Future[Response]] = {}
    mq = loop.run_until_complete(create_mq(loop, MQ_URL, uuids_map))
    loop.create_task(mq.recv())

    bot = Bot(TELEGRAM_API_TOKEN, parse_mode="MarkdownV2")
    dp = Dispatcher()
    dp["base_url"] = TELEGRAM_WEBHOOK_HOST

    router = Router(bot, mq, uuids_map)
    aiogram_router = AiogramRouter()
    aiogram_router.message(router.help, Command(commands=["start", "help"]))
    dp.include_router(aiogram_router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = Application()
    app["bot"] = bot
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(
        app, path=TELEGRAM_WEBHOOK_PATH
    )
    setup_application(app, dp, bot=bot)

    web.run_app(
        app, host=TELEGRAM_WEBAPP_HOST, port=int(TELEGRAM_WEBAPP_PORT), loop=loop
    )
    # dp.register_message_handler(router.help, commands=["start", "help"])
    # dp.register_message_handler(
    #     dp.async_task(router.general), commands=[COMMAND_GENERAL, "g"]
    # )
    # dp.register_message_handler(
    #     dp.async_task(router.custom), commands=[COMMAND_CUSTOM, "c"]
    # )
    # dp.register_callback_query_handler(dp.async_task(router.callback))

    # TODO: handle reconnect

    # start_bot(loop, dp, bot)


if __name__ == "__main__":
    loop = get_event_loop()
    start_service(loop)
