from typing import Optional

RESPONSE_STATUS_OK = "Ok"
RESPONSE_STATUS_FORBIDDEN = "Forbidden"
RESPONSE_STATUS_NOT_FOUND = "NotFound"
RESPONSE_STATUS_INTERNAL_ERROR = "InternalError"
RESPONSE_STATUS_NOT_IMPLEMENTED = "NotImplemented"

COMMAND_GENERAL = "general"
COMMAND_CUSTOM = "custom"


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


class GenerateResponsePayload:
    result: str

    def __init__(self, data: dict):
        self.result = data.get("msg")  # type: ignore


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
