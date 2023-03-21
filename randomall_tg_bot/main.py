import logging
from asyncio import AbstractEventLoop, Future, get_event_loop

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from randomall_tg_bot.config import DEBUG, MQ_URL, TELEGRAM_API_TOKEN
from randomall_tg_bot.messages import Response
from randomall_tg_bot.mq import create_mq
from randomall_tg_bot.router import Router


def start_service(loop: AbstractEventLoop):
    level = logging.DEBUG if DEBUG else logging.INFO
    logging.basicConfig(level=level)
    uuids_map: dict[str, Future[Response]] = {}
    mq = loop.run_until_complete(create_mq(loop, MQ_URL, uuids_map))

    router = Router(mq, uuids_map)

    # TODO: handle reconnect
    mq_recv_task = loop.create_task(mq.recv())

    async def on_shutdown(_: Application) -> None:
        mq_recv_task.cancel()
        await mq.close()

    app = (
        Application.builder()
        .token(TELEGRAM_API_TOKEN)
        .post_shutdown(on_shutdown)
        .build()
    )

    app.add_handler(CommandHandler(["start", "help"], router.help))
    app.add_handler(CommandHandler(["general", "g"], router.general))
    app.add_handler(CommandHandler(["custom", "c"], router.custom))
    app.add_handler(CallbackQueryHandler(router.callback))

    app.run_polling()


if __name__ == "__main__":
    loop = get_event_loop()
    start_service(loop)
