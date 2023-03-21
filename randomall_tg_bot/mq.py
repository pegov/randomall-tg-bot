from asyncio import AbstractEventLoop, Future

import orjson
from aio_pika import Message, connect_robust
from aio_pika.abc import AbstractExchange, AbstractQueue, AbstractRobustConnection

from randomall_tg_bot.messages import (
    COMMAND_CUSTOM_INFO,
    COMMAND_CUSTOM_RESULT_MULTI,
    COMMAND_CUSTOM_RESULT_SINGLE,
    COMMAND_GENERAL_RESULT,
    CustomRequestPayload,
    CustomWithButtonIdRequestPayload,
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
                    data = orjson.loads(message.body)
                    uuid = data.get("uuid")

                    try:
                        result_future = self.uuids_map.pop(uuid)
                        response = Response.from_dict(data)
                        result_future.set_result(response)
                    except KeyError:
                        continue

    async def close(self) -> None:
        await self.connection.close()

    async def general_result(self, uuid: str, name: str) -> None:
        payload = GeneralRequestPayload(name)
        request = Request(uuid, COMMAND_GENERAL_RESULT, payload.to_dict())
        await self._make_request(request)

    async def custom_info(self, uuid: str, id: int) -> None:
        payload = CustomRequestPayload(id)
        request = Request(uuid, COMMAND_CUSTOM_INFO, payload.to_dict())
        await self._make_request(request)

    async def custom_result(self, uuid: str, id: int) -> None:
        payload = CustomRequestPayload(id)
        request = Request(uuid, COMMAND_CUSTOM_RESULT_SINGLE, payload.to_dict())
        await self._make_request(request)

    async def custom_result_with_button_id(
        self,
        uuid: str,
        id: int,
        button_id: int,
    ) -> None:
        payload = CustomWithButtonIdRequestPayload(id, button_id)
        request = Request(uuid, COMMAND_CUSTOM_RESULT_MULTI, payload.to_dict())
        await self._make_request(request)

    async def _make_request(self, request: Request) -> None:
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
    channel_a = await connection.channel()
    channel_b = await connection.channel()

    # Creating exchange
    request_exchange = await channel_a.declare_exchange("telegram_request_exchange")

    # Declaring queues
    request_queue = await channel_a.declare_queue(QUEUE_TELEGRAM_REQUEST)
    await request_queue.bind(request_exchange, QUEUE_TELEGRAM_REQUEST)

    response_queue = await channel_b.declare_queue(QUEUE_TELEGRAM_RESPONSE)

    return MQ(connection, request_queue, response_queue, request_exchange, uuids_map)
