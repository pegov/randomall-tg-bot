import asyncio
from uuid import uuid4

from aiogram import Bot, types

from randomall_tg_bot.messages import (
    COMMAND_CUSTOM,
    COMMAND_GENERAL,
    RESPONSE_STATUS_FORBIDDEN,
    RESPONSE_STATUS_NOT_FOUND,
    RESPONSE_STATUS_OK,
    GenerateResponsePayload,
    Response,
)
from randomall_tg_bot.mq import MQ

TIMEOUT = 10.0

HELP_MESSAGE = """*Официальный бот randomall\\.ru*
Поддерживает встроенные и публичные пользовательские генераторы\\.

Cписок команд:
/general \\- Выбрать встроенный генератор
/custom \\- Пользовательские генераторы
/help \\- Показать это сообщение
"""

CUSTOM_MESSAGE = """*Пользовательские генераторы*

/custom _id_ \\- Получить результат генерации
_id_ можно посмотреть в адресной строке браузера на странице генератора

Пока поддерживаются только публичные генераторы
"""

SERVER_ERROR_MESSAGE = "Серверная ошибка"
GENERATOR_NOT_FOUND_MESSAGE = "Генератор не найден"
FORBIDDEN_MESSAGE = "Приватный генератор"
ID_MUST_BE_A_NUMBER_MESSAGE = "id должен быть числом"

GENERAL: list[tuple[str, str]] = [
    ("Фэнтези имя", "fantasy_name"),
    ("Внешность мужская", "appearance_male"),
    ("Внешность женская", "appearance_female"),
    ("Второстепенный персонаж", "crowd"),
    ("Характер", "character"),
    ("Мотивация", "motivation"),
    ("Способности", "abilities"),
    ("Особенности", "features"),
    ("Профессия", "jobs"),
    ("Раса", "race"),
    ("Суперспособность", "superpowers"),
    ("Сюжет", "plot"),
    ("Ключевые слова для сюжета", "plotkeys"),
    ("Неловкий момент", "awkward_moment"),
    ("Неожиданный поворот", "unexpected_event"),
    ("Название книги", "bookname"),
    ("Название вымышленной страны", "fantasy_country"),
    ("Название вымышленного города", "fantasy_town"),
    ("Название вымышненного континента", "fantasy_continent"),
    ("Мужское имя", "names_male"),
    ("Женское имя", "names_female"),
    ("Фамилия", "surnames"),
    ("Страна", "countries"),
    ("Русский город", "cities"),
]

ACTION_FIRST = "first"
ACTION_REPEAT = "repeat"


def escape_text(text: str) -> str:
    """MarkdownV2 escape"""
    for ch in (
        "_",
        "*",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ):
        text = text.replace(ch, f"\\{ch}")
    return text


def get_general_markup() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        1,
        [
            [
                types.InlineKeyboardButton(
                    name, callback_data=f"general:{ACTION_FIRST}:{target}"
                ),
            ]
            for name, target in GENERAL
        ],
    )


def get_repeat_markup(command: str, target: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        1,
        [
            [
                types.InlineKeyboardButton(
                    "Ещё", callback_data=f"{command}:{ACTION_REPEAT}:{target}"
                )
            ]
        ],
    )


class Router:
    def __init__(self, bot: Bot, mq: MQ, uuids_map: dict[str, asyncio.Future]):
        self.bot = bot
        self.mq = mq
        self.uuids_map = uuids_map

    async def help(self, message: types.Message) -> None:
        await message.answer(HELP_MESSAGE)

    async def general(self, message: types.Message) -> None:
        await message.answer("Выберите:", reply_markup=get_general_markup())

    async def custom(self, message: types.Message) -> None:
        args = message.get_args()
        if args is None or args.strip() == "":
            await message.answer(CUSTOM_MESSAGE)
            return

        try:
            id = int(args)
        except ValueError:
            await message.answer(ID_MUST_BE_A_NUMBER_MESSAGE)
            return

        uuid, response_future = self._create_response_future()

        await self.mq.custom_request(uuid, id)

        try:
            response = await asyncio.wait_for(response_future, timeout=TIMEOUT)
            if response.status == RESPONSE_STATUS_OK:
                assert response.payload is not None
                payload = GenerateResponsePayload(response.payload)
                await message.answer(
                    escape_text(payload.result),
                    reply_markup=get_repeat_markup(COMMAND_CUSTOM, str(id)),
                )
            elif response.status == RESPONSE_STATUS_FORBIDDEN:
                await message.answer(FORBIDDEN_MESSAGE)
            elif response.status == RESPONSE_STATUS_NOT_FOUND:
                await message.answer(GENERATOR_NOT_FOUND_MESSAGE)
            else:
                await message.answer(SERVER_ERROR_MESSAGE)
        except asyncio.exceptions.TimeoutError:
            await message.answer(SERVER_ERROR_MESSAGE)
        finally:
            self._delete_response_future(uuid)

    async def callback(self, cq: types.CallbackQuery) -> None:
        cq_object = cq.to_python()
        chat_id = cq_object.get("message").get("chat").get("id")  # type: ignore
        message_id = cq_object.get("message").get("message_id")  # type: ignore
        cq_data = cq_object.get("data")

        if cq_data is None:
            return

        is_general = cq_data.startswith(COMMAND_GENERAL)
        is_custom = cq_data.startswith(COMMAND_CUSTOM)

        if is_general:
            _, action, name = cq_data.split(":", 2)

            uuid, response_future = self._create_response_future()

            await self.mq.general_request(uuid, name)

            try:
                response = await asyncio.wait_for(response_future, timeout=TIMEOUT)
                if response.status == RESPONSE_STATUS_OK:
                    assert response.payload is not None
                    payload = GenerateResponsePayload(response.payload)
                    if name == "superpowers":
                        title, description = payload.result.split(";", 1)
                        text = f"*{escape_text(title)}*\n{escape_text(description)}"
                    else:
                        text = escape_text(payload.result)

                    if action == ACTION_REPEAT:
                        await self.bot.edit_message_reply_markup(
                            chat_id,
                            message_id=message_id,
                            reply_markup=None,
                        )
                        await self.bot.send_message(
                            chat_id,
                            text,
                            reply_markup=get_repeat_markup(COMMAND_GENERAL, name),
                        )
                    else:
                        await self.bot.edit_message_text(
                            text,
                            chat_id,
                            message_id,
                            reply_markup=get_repeat_markup(COMMAND_GENERAL, name),
                        )
                elif response.status == RESPONSE_STATUS_NOT_FOUND:
                    await self.bot.send_message(chat_id, GENERATOR_NOT_FOUND_MESSAGE)
                else:
                    await self.bot.send_message(chat_id, SERVER_ERROR_MESSAGE)
            except asyncio.exceptions.TimeoutError:
                await self.bot.send_message(chat_id, SERVER_ERROR_MESSAGE)
            finally:
                self._delete_response_future(uuid)

        elif is_custom:
            _, action, id = cq_data.split(":", 2)

            try:
                id = int(id)
            except ValueError:
                await self.bot.send_message(chat_id, ID_MUST_BE_A_NUMBER_MESSAGE)
                return

            uuid, response_future = self._create_response_future()

            await self.mq.custom_request(uuid, id)

            try:
                response = await asyncio.wait_for(response_future, timeout=TIMEOUT)
                if response.status == RESPONSE_STATUS_OK:
                    assert response.payload is not None
                    payload = GenerateResponsePayload(response.payload)
                    text = escape_text(payload.result)
                    if action == ACTION_REPEAT:
                        await self.bot.edit_message_reply_markup(
                            chat_id,
                            message_id=message_id,
                            reply_markup=None,
                        )
                        await self.bot.send_message(
                            chat_id,
                            text,
                            reply_markup=get_repeat_markup(COMMAND_CUSTOM, str(id)),
                        )
                    else:
                        await self.bot.edit_message_text(
                            text,
                            chat_id,
                            message_id,
                            reply_markup=get_repeat_markup(COMMAND_CUSTOM, str(id)),
                        )
                elif response.status == RESPONSE_STATUS_FORBIDDEN:
                    await self.bot.send_message(chat_id, FORBIDDEN_MESSAGE)
                elif response.status == RESPONSE_STATUS_NOT_FOUND:
                    await self.bot.send_message(chat_id, GENERATOR_NOT_FOUND_MESSAGE)
                else:
                    await self.bot.send_message(chat_id, SERVER_ERROR_MESSAGE)
            except asyncio.exceptions.TimeoutError:
                await self.bot.send_message(chat_id, SERVER_ERROR_MESSAGE)
            finally:
                self._delete_response_future(uuid)

    def _create_response_future(self) -> tuple[str, asyncio.Future[Response]]:
        """Return uuid and future"""
        uuid = str(uuid4())
        response_future: asyncio.Future[Response] = asyncio.Future()
        self.uuids_map.update({uuid: response_future})
        return uuid, response_future

    def _delete_response_future(self, uuid: str) -> None:
        """Delete future from map if it exists"""
        try:
            self.uuids_map.pop(uuid)
        except KeyError:
            pass
