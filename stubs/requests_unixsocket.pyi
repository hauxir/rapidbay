# Type stub for requests_unixsocket

from typing import Any

class Response:
    def json(self) -> Any: ...


class Session:
    def get(self, url: str) -> Response: ...

    def post(self, url: str, json: Any = None) -> Response: ...
