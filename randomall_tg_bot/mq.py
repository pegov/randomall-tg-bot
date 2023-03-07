import logging
from asyncio import AbstractEventLoop, Future

import orjson
from aio_pika import Message, connect_robust
from aio_pika.abc import AbstractExchange, AbstractQueue, AbstractRobustConnection

from randomall_tg_bot.messages import (
    COMMAND_CUSTOM,
    COMMAND_GENERAL,
    CustomRequestPayload,
    GeneralRequestPayload,
    Request,
    Response,
)

QUEUE_TELEGRAM_REQUEST = "telegram_request"
QUEUE_TELEGRAM_RESPONSE = "telegram_response"


class MQ:
    connection: AbstractRobustConnection
    request_queue: AbstractQueue
    response_queue: AbstractQueue
    request_exchange: AbstractExchange

    uuids_map: dict[str, Future[Response]]

    def __init__(
        self,
        connection: AbstractRobustConnection,
        request_queue: AbstractQueue,
        response_queue: AbstractQueue,
        request_exchange: AbstractExchange,
        uuids_map: dict[str, Future[Response]],
    ) -> None:
        self.connection = connection
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.request_exchange = request_exchange
        self.uuids_map = uuids_map

    async def recv(self) -> None:
        async with self.response_queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    logging.debug(f"Response queue: received {message}")
                    data = orjson.loads(message.body)
                    uuid = data.get("uuid")

                    try:
                        result_future = self.uuids_map.pop(uuid)
                        response = Response.from_dict(data)
                        result_future.set_result(response)
                    except KeyError:
                        continue

                    logging.debug(self.uuids_map)

    async def close(self) -> None:
        await self.connection.close()

    async def general_request(self, uuid: str, name: str) -> None:
        payload = GeneralRequestPayload(name)
        request = Request(uuid, COMMAND_GENERAL, payload.to_dict())
        await self._generate_request(request)

    async def custom_request(self, uuid: str, id: int) -> None:
        payload = CustomRequestPayload(id)
        request = Request(uuid, COMMAND_CUSTOM, payload.to_dict())
        await self._generate_request(request)

    async def _generate_request(self, request: Request) -> None:
        message = Message(
            orjson.dumps(request.to_dict()),
            content_type="text/plain",
            expiration=10,
        )
        await self.request_exchange.publish(
            message,
            routing_key=QUEUE_TELEGRAM_REQUEST,
        )


async def create_mq(
    loop: AbstractEventLoop,
    amqp_url: str,
    uuids_map: dict[str, Future],
) -> MQ:
    connection = await connect_robust(amqp_url, loop=loop)

    # Creating channels
    channel_a = await connection.channel(3)
    channel_b = await connection.channel(4)

    # Creating exchange
    request_exchange = await channel_a.declare_exchange("telegram_request_exchange")

    # Declaring queues
    request_queue = await channel_a.declare_queue(QUEUE_TELEGRAM_REQUEST)
    await request_queue.bind(request_exchange, QUEUE_TELEGRAM_REQUEST)

    response_queue = await channel_b.declare_queue(QUEUE_TELEGRAM_RESPONSE)

    return MQ(connection, request_queue, response_queue, request_exchange, uuids_map)
