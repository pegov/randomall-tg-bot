import asyncio
from typing import List
from uuid import uuid4

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from randomall_tg_bot.messages import (
    BUTTONS_MODE_DEFAULT,
    BUTTONS_MODE_RENAME,
    COMMAND_CUSTOM_INFO,
    COMMAND_CUSTOM_RESULT_MULTI,
    COMMAND_CUSTOM_RESULT_SINGLE,
    COMMAND_GENERAL_RESULT,
    RESPONSE_STATUS_FORBIDDEN,
    RESPONSE_STATUS_NOT_FOUND,
    RESPONSE_STATUS_OK,
    ButtonsCustom,
    ButtonsCustomItem,
    ButtonsRename,
    CustomInfoResponsePayload,
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

MODE_SINGLE = "single"
MODE_MULTI = "multi"


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


def get_general_first_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup.from_column(
        [
            InlineKeyboardButton(
                name, callback_data=f"{COMMAND_GENERAL_RESULT}:{ACTION_FIRST}:{target}"
            )
            for name, target in GENERAL
        ]
    )


def get_general_repeat_markup(target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup.from_column(
        [
            InlineKeyboardButton(
                "Ещё",
                callback_data=f"{COMMAND_GENERAL_RESULT}:{ACTION_REPEAT}:{target}",
            )
        ],
    )


def get_custom_single_button_first_markup(
    button_name: str,
    target: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup.from_column(
        [
            InlineKeyboardButton(
                button_name,
                callback_data=f"{COMMAND_CUSTOM_RESULT_SINGLE}:{MODE_SINGLE}:{ACTION_FIRST}:{target}",
            )
        ]
    )


def get_custom_single_button_repeat_markup(target: str):
    return InlineKeyboardMarkup.from_column(
        [
            InlineKeyboardButton(
                "Инфо", callback_data=f"{COMMAND_CUSTOM_INFO}:{target}"
            ),
            InlineKeyboardButton(
                "Ещё",
                callback_data=f"{COMMAND_CUSTOM_RESULT_SINGLE}:{MODE_SINGLE}:{ACTION_REPEAT}:{target}",
            ),
        ],
    )


def get_custom_multiple_buttons_first_markup(
    items: List[ButtonsCustomItem],
    target: str,
) -> InlineKeyboardMarkup:
    rows = []
    row = []
    current_row = 0
    for i, item in enumerate(items):
        if item.row == current_row:
            row.append(
                InlineKeyboardButton(
                    item.title,
                    callback_data=f"{COMMAND_CUSTOM_RESULT_MULTI}:{MODE_MULTI}:{ACTION_FIRST}:{target}:{i+1}",
                )
            )
        else:
            rows.append(row.copy())
            current_row += 1
            row.clear()

    if len(row) > 0:
        rows.append(row)

    return InlineKeyboardMarkup(rows)


def get_custom_multiple_buttons_repeat_markup(
    target: str,
    button_id: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup.from_column(
        [
            InlineKeyboardButton(
                "Инфо", callback_data=f"{COMMAND_CUSTOM_INFO}:{target}"
            ),
            InlineKeyboardButton(
                "Ещё",
                callback_data=f"{COMMAND_CUSTOM_RESULT_MULTI}:{MODE_MULTI}:{ACTION_REPEAT}:{target}:{button_id}",
            ),
        ]
    )


class Router:
    def __init__(self, mq: MQ, uuids_map: dict[str, asyncio.Future]):
        self.mq = mq
        self.uuids_map = uuids_map

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN_V2)  # type: ignore

    async def general(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Выберите:", reply_markup=get_general_first_markup())  # type: ignore

    async def custom(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if context.args is None or len(context.args) == 0:
            await update.message.reply_text(  # type: ignore
                CUSTOM_MESSAGE, parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        arg = context.args[0]
        if arg.strip() == "":
            await update.message.reply_text(  # type: ignore
                CUSTOM_MESSAGE, parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        try:
            id = int(arg)
        except ValueError:
            await update.message.reply_text(ID_MUST_BE_A_NUMBER_MESSAGE)  # type: ignore
            return

        uuid, response_future = self._create_response_future()

        await self.mq.custom_info(uuid, id)

        try:
            response = await asyncio.wait_for(response_future, timeout=TIMEOUT)
            if response.status == RESPONSE_STATUS_OK:
                assert response.payload is not None
                payload = CustomInfoResponsePayload(response.payload)
                buttons = payload.format.get("buttons")  # type: ignore
                buttons_mode = buttons.get("mode")  # type: ignore

                if buttons_mode == BUTTONS_MODE_DEFAULT:
                    markup = get_custom_single_button_first_markup(
                        "Сгенерировать", str(id)
                    )
                elif buttons_mode == BUTTONS_MODE_RENAME:
                    markup = get_custom_single_button_first_markup(
                        ButtonsRename(buttons).title,  # type: ignore
                        str(id),
                    )
                else:  # custom
                    markup = get_custom_multiple_buttons_first_markup(
                        ButtonsCustom(buttons).items,  # type: ignore
                        str(id),
                    )

                text = f"*{escape_text(payload.title)}*\n{escape_text(payload.description)}"
                await update.message.reply_text(  # type: ignore
                    text,
                    reply_markup=markup,
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
            elif response.status == RESPONSE_STATUS_FORBIDDEN:
                await update.message.reply_text(FORBIDDEN_MESSAGE)  # type: ignore
            elif response.status == RESPONSE_STATUS_NOT_FOUND:
                await update.message.reply_text(GENERATOR_NOT_FOUND_MESSAGE)  # type: ignore
            else:
                await update.message.reply_text(SERVER_ERROR_MESSAGE)  # type: ignore
        except asyncio.exceptions.TimeoutError:
            await update.message.reply_text(SERVER_ERROR_MESSAGE)  # type: ignore
        finally:
            self._delete_response_future(uuid)

    async def callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        query = update.callback_query
        await query.answer()  # type: ignore

        is_general_result = query.data.startswith("general_result")  # type: ignore
        is_custom_info = query.data.startswith("custom_info")  # type: ignore
        is_custom_result = query.data.startswith("custom_result")  # type: ignore

        if is_general_result:
            _, action, name = query.data.split(":", 2)  # type: ignore

            uuid, response_future = self._create_response_future()

            await self.mq.general_result(uuid, name)

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
                        await update.effective_message.edit_reply_markup()  # type: ignore
                        await update.effective_message.reply_text(  # type: ignore
                            text,
                            reply_markup=get_general_repeat_markup(name),
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                    else:
                        await update.effective_message.edit_text(  # type: ignore
                            text,
                            reply_markup=get_general_repeat_markup(name),
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                elif response.status == RESPONSE_STATUS_NOT_FOUND:
                    await update.effective_message.reply_text(  # type: ignore
                        GENERATOR_NOT_FOUND_MESSAGE
                    )
                else:
                    await update.effective_message.reply_text(SERVER_ERROR_MESSAGE)  # type: ignore
            except asyncio.exceptions.TimeoutError:
                await update.effective_message.reply_text(SERVER_ERROR_MESSAGE)  # type: ignore
            finally:
                self._delete_response_future(uuid)

        elif is_custom_info:
            _, id = query.data.split(":", 1)  # type: ignore

            try:
                id = int(id)
            except ValueError:
                await update.effective_message.reply_text(ID_MUST_BE_A_NUMBER_MESSAGE)  # type: ignore
                return

            uuid, response_future = self._create_response_future()

            await self.mq.custom_info(uuid, id)

            try:
                response = await asyncio.wait_for(response_future, timeout=TIMEOUT)
                if response.status == RESPONSE_STATUS_OK:
                    assert response.payload is not None
                    payload = CustomInfoResponsePayload(response.payload)
                    text = f"*{payload.title}*\n{escape_text(payload.description)}"
                    buttons = payload.format.get("buttons")  # type: ignore
                    buttons_mode = buttons.get("mode")  # type: ignore
                    if buttons_mode == BUTTONS_MODE_DEFAULT:
                        markup = get_custom_single_button_first_markup(
                            "Сгенерировать", str(id)
                        )
                    elif buttons_mode == BUTTONS_MODE_RENAME:
                        markup = get_custom_single_button_first_markup(
                            ButtonsRename(buttons).title,  # type: ignore
                            str(id),
                        )
                    else:  # custom
                        markup = get_custom_multiple_buttons_first_markup(
                            ButtonsCustom(buttons).items,  # type: ignore
                            str(id),
                        )
                    await update.effective_message.edit_reply_markup()  # type: ignore
                    await update.effective_message.reply_text(  # type: ignore
                        text,
                        reply_markup=markup,
                        parse_mode=ParseMode.MARKDOWN_V2,
                    )
                elif response.status == RESPONSE_STATUS_FORBIDDEN:
                    await update.effective_message.reply_text(FORBIDDEN_MESSAGE)  # type: ignore
                elif response.status == RESPONSE_STATUS_NOT_FOUND:
                    await update.effective_message.reply_text(  # type: ignore
                        GENERATOR_NOT_FOUND_MESSAGE
                    )
                else:
                    await update.effective_message.reply_text(SERVER_ERROR_MESSAGE)  # type: ignore
            except asyncio.exceptions.TimeoutError:
                await update.effective_message.reply_text(SERVER_ERROR_MESSAGE)  # type: ignore
            finally:
                self._delete_response_future(uuid)

        elif is_custom_result:
            _, mode, action, rest = query.data.split(":", 3)  # type: ignore

            if mode == MODE_SINGLE:
                id = rest
                button_id = None
            else:
                id, button_id = rest.split(":", 1)
                button_id = int(button_id)

            try:
                id = int(id)
            except ValueError:
                await update.effective_message.reply_text(ID_MUST_BE_A_NUMBER_MESSAGE)  # type: ignore
                return

            uuid, response_future = self._create_response_future()

            if mode == MODE_SINGLE:
                await self.mq.custom_result(uuid, id)
            else:
                assert button_id is not None
                await self.mq.custom_result_with_button_id(uuid, id, button_id)

            try:
                response = await asyncio.wait_for(response_future, timeout=TIMEOUT)
                if response.status == RESPONSE_STATUS_OK:
                    assert response.payload is not None
                    payload = GenerateResponsePayload(response.payload)
                    if mode == MODE_SINGLE:
                        markup = get_custom_single_button_repeat_markup(str(id))
                    else:  # multi
                        assert button_id is not None
                        markup = get_custom_multiple_buttons_repeat_markup(
                            str(id), str(button_id)
                        )
                    text = escape_text(payload.result)
                    if action == ACTION_REPEAT:
                        await update.effective_message.edit_reply_markup()  # type: ignore
                        await update.effective_message.reply_text(  # type: ignore
                            text,
                            reply_markup=markup,
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                    else:
                        await update.effective_message.edit_text(  # type: ignore
                            text,
                            reply_markup=markup,
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                elif response.status == RESPONSE_STATUS_FORBIDDEN:
                    await update.effective_message.reply_text(FORBIDDEN_MESSAGE)  # type: ignore
                elif response.status == RESPONSE_STATUS_NOT_FOUND:
                    await update.effective_message.reply_text(  # type: ignore
                        GENERATOR_NOT_FOUND_MESSAGE
                    )
                else:
                    await update.effective_message.reply_text(SERVER_ERROR_MESSAGE)  # type: ignore
            except asyncio.exceptions.TimeoutError:
                await update.effective_message.reply_text(SERVER_ERROR_MESSAGE)  # type: ignore
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
