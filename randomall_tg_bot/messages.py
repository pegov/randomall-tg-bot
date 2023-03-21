from typing import List, Optional

RESPONSE_STATUS_OK = "Ok"
RESPONSE_STATUS_FORBIDDEN = "Forbidden"
RESPONSE_STATUS_NOT_FOUND = "NotFound"
RESPONSE_STATUS_INTERNAL_ERROR = "InternalError"
RESPONSE_STATUS_NOT_IMPLEMENTED = "NotImplemented"

COMMAND_GENERAL_RESULT = "general_result"
COMMAND_CUSTOM_INFO = "custom_info"
COMMAND_CUSTOM_RESULT_SINGLE = "custom_result_single"
COMMAND_CUSTOM_RESULT_MULTI = "custom_result_multi"

BUTTONS_MODE_DEFAULT = "default"
BUTTONS_MODE_RENAME = "rename"
BUTTONS_MODE_CUSTOM = "custom"


class Request:
    uuid: str
    command: str
    payload: dict

    def __init__(self, uuid: str, command: str, payload: dict):
        self.uuid = uuid
        self.command = command
        self.payload = payload

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "command": self.command,
            "payload": self.payload,
        }


class GeneralRequestPayload:
    name: str

    def __init__(self, name: str):
        self.name = name

    def to_dict(self) -> dict:
        return {"name": self.name}


class CustomRequestPayload:
    id: int

    def __init__(self, id: int):
        self.id = id

    def to_dict(self) -> dict:
        return {"id": self.id}


class CustomWithButtonIdRequestPayload:
    id: int
    button_id: int

    def __init__(self, id: int, button_id: int):
        self.id = id
        self.button_id = button_id

    def to_dict(self) -> dict:
        return {"id": self.id, "button_id": self.button_id}


class ButtonsRename:
    title: str

    def __init__(self, data: dict) -> None:
        self.title = data.get("title")  # type: ignore


class ButtonsCustomItem:
    title: str
    row: int

    def __init__(self, data: dict) -> None:
        self.title = data.get("title")  # type: ignore
        self.row = data.get("row")  # type: ignore


class ButtonsCustom:
    items: List[ButtonsCustomItem]

    def __init__(self, data: dict) -> None:
        self.items = [
            ButtonsCustomItem(item_data) for item_data in data.get("items")  # type: ignore
        ]


class GenerateResponsePayload:
    result: str

    def __init__(self, data: dict):
        self.result = data.get("msg")  # type: ignore


class CustomInfoResponsePayload:
    id: int
    title: str
    description: str

    format: dict

    def __init__(self, data: dict) -> None:
        self.id = data.get("id")  # type: ignore
        self.title = data.get("title")  # type: ignore
        self.description = data.get("description")  # type: ignore
        self.format = data.get("format")  # type: ignore


class Response:
    uuid: str
    command: str
    status: str
    payload: Optional[dict]

    def __init__(
        self,
        uuid: str,
        command: str,
        status: str,
        payload: Optional[dict],
    ) -> None:
        self.uuid = uuid
        self.command = command
        self.status = status
        self.payload = payload

    @classmethod
    def from_dict(cls, data: dict) -> "Response":
        return cls(
            data.get("uuid"),  # type: ignore
            data.get("command"),  # type: ignore
            data.get("status"),  # type: ignore
            data.get("payload"),  # type: ignore
        )
