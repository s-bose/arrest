from dataclasses import dataclass
from datetime import timedelta
from typing import Generic, TypeVar

import httpx

T = TypeVar("T")


@dataclass(frozen=True)
class Response(Generic[T]):
    data: T
    status_code: int
    url: httpx.URL
    elapsed: timedelta | None
    raw: httpx.Response
    request: httpx.Request | None

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_redirect(self) -> bool:
        return 300 <= self.status_code < 400

    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        return 500 <= self.status_code < 600
