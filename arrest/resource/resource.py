from typing import Optional, List, Type
from pydantic import BaseModel
import httpx

from arrest.http import Methods


class ResourceHandler:
    method: Methods
    route: str
    request: Optional[Type[BaseModel]]
    response: Optional[Type[BaseModel]]
    kwargs: Optional[dict]


class Resource:
    _handlers: List[ResourceHandler]

    def __init__(
        self, name: str, route: str, response_model: Optional[Type[BaseModel]] = None
    ) -> None:
        self.base_url = None
        self.name = name
        self.route = route
        self.response_model = response_model
        self._handlers = []

    def add_handler(
        self,
        method: Methods,
        route: str,
        *,
        request: Optional[Type[BaseModel]] = None,
        response: Optional[Type[BaseModel]] = None,
        **kwargs,
    ):
        self._handlers.append(
            ResourceHandler(
                method=method,
                route=route,
                request=request,
                response=response,
                kwargs=kwargs,
            )
        )

    async def get():
        pass

    async def post():
        pass

    async def put():
        pass

    async def patch():
        pass

    async def delete():
        pass

    # async def _make_request_async(
    #     self,
    #     method: Methods,
    #     url: str,
    #     path: Optional[dict],
    #     query: Optional[dict],
    #     body: Optional[dict],
    #     headers: Optional[dict],
    #     **kwargs,
    # ):
    #     async with
