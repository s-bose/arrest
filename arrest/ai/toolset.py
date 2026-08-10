from dataclasses import dataclass
from typing import Any, Mapping, cast

import httpx
from pydantic import TypeAdapter
from pydantic_ai import RunContext
from pydantic_ai.exceptions import ModelRetry, ToolFailed, UserError
from pydantic_ai.tools import AgentDepsT, ToolDefinition
from pydantic_ai.toolsets import AbstractToolset, ToolsetTool
from pydantic_core import SchemaValidator

from arrest._config import ArrestConfig
from arrest.ai.meta import ToolMeta
from arrest.ai.schema import build_args_model
from arrest.http import Methods
from arrest.exceptions import ArrestHTTPException, HandlerNotFound, RequestError
from arrest.handler import ResourceHandler
from arrest.resource import Resource
from arrest.response import Response as ArrestResponse
from arrest.service import Service
from arrest.utils import gen_unique_handler_name, sanitize_name

# Transient HTTP status codes
DEFAULT_RETRY_ON_ERRORS = frozenset({408, 429, 500, 502, 503, 504})

# { "resource_1", "resource_2" }
# { "resource_1": {"GET", "POST"} }
# { "resource_1": {"GET": {"/users", "/profile"}, "POST": {"/shipments"}} }
IncludeExclude = (
    set[str] | Mapping[str, set[Methods]] | Mapping[str, Mapping[Methods, set[str]]]
)


def matches_include_exclude(
    spec: IncludeExclude, *, resource: str, method: Methods, route: str
) -> bool:
    if isinstance(spec, (set, frozenset)):
        return resource in spec

    if resource not in spec:
        return False
    methods = spec[resource]

    if isinstance(methods, (set, frozenset)):
        return method in methods

    if method not in methods:
        return False
    return route in methods[method]


@dataclass(kw_only=True)
class ArrestToolsetTool(ToolsetTool[AgentDepsT]):
    resource: Resource
    handler: ResourceHandler


class ArrestToolset(AbstractToolset[AgentDepsT]):
    def __init__(
        self,
        service: Service,
        *,
        id: Any = None,
        include: IncludeExclude | None = None,
        exclude: IncludeExclude | None = None,
        tool_max_retries: int | None = None,
        config: ArrestConfig | None = None,
        retry_on_errors: list[int] | None = None,
    ):
        self._id = (
            id if id is not None else f"arrest-{sanitize_name(service.name)}-service"
        )
        self._service = service
        self._include = include
        self._exclude = exclude
        self._tool_max_retries = tool_max_retries
        self._config = config
        self._retry_on_errors = (
            frozenset(retry_on_errors)
            if retry_on_errors is not None
            else DEFAULT_RETRY_ON_ERRORS
        )

        self._tools: dict[str, ToolsetTool[AgentDepsT]] | None = None
        self._client: httpx.AsyncClient | None = None
        self._entered = False
        self._original_configs: dict[str, ArrestConfig | None] = {}

    @property
    def id(self) -> str | None:
        return self._id

    async def __aenter__(self) -> "ArrestToolset[AgentDepsT]":
        if self._entered:
            return self
        self._entered = True

        if self._config is None or self._config.client is None:
            # base_url must live on the client itself once `config.client`
            # is set. `resource.request()` only applies `resource.base_url`
            # when it opens its own ad-hoc client.
            self._client = httpx.AsyncClient(base_url=self._service.url)
            base_config = ArrestConfig(client=self._client)
        else:
            base_config = ArrestConfig()

        effective_config = (
            base_config.merge(self._config) if self._config else base_config
        )

        for resource in self._service.resources.values():
            self._original_configs[resource.name] = resource.config
            resource.config = (
                resource.config.merge(effective_config)
                if resource.config
                else effective_config
            )
        return self

    async def __aexit__(self, *_args) -> bool | None:
        if not self._entered:
            return None

        for resource in self._service.resources.values():
            if resource.name in self._original_configs:
                resource.config = self._original_configs[resource.name]
        self._original_configs = {}

        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._entered = False
        return None

    async def get_tools(
        self,
        ctx: RunContext[AgentDepsT],
    ) -> dict[str, ToolsetTool[AgentDepsT]]:
        if self._tools is None:
            self._tools = self._build_tools(ctx)
        return self._tools

    def _build_tools(
        self, ctx: RunContext[AgentDepsT]
    ) -> dict[str, ToolsetTool[AgentDepsT]]:
        tools: dict[str, ToolsetTool[AgentDepsT]] = {}

        for resource in self._service.resources.values():
            for handler in resource.routes.values():
                meta = handler.tool_meta
                if meta is None or not meta.include:
                    continue

                if self._include is not None and not matches_include_exclude(
                    self._include,
                    resource=resource.name,
                    method=handler.method,
                    route=handler.route,
                ):
                    continue
                if self._exclude is not None and matches_include_exclude(
                    self._exclude,
                    resource=resource.name,
                    method=handler.method,
                    route=handler.route,
                ):
                    continue

                name = meta.name or gen_unique_handler_name(
                    resource.name, route=handler.route, method=handler.method
                )

                if name in tools:
                    raise UserError(
                        f"Duplicate tool name {name!r} in {self.label!r}. Set "
                        "`tool_meta.name` on the conflicting handlers to disambiguate."
                    )

                handler_schema = build_args_model(handler, resource_name=resource.name)
                if handler_schema is None:
                    continue

                description = meta.description or (
                    f"{handler.method} {handler.route} on the {resource.name!r} resource"
                )
                tool_max_retries = (
                    self._tool_max_retries
                    if self._tool_max_retries is not None
                    else ctx.max_retries
                )

                return_schema = None
                include_return_schema = False
                if handler_schema.return_model is not None:
                    return_schema = TypeAdapter(
                        handler_schema.return_model
                    ).json_schema()
                    include_return_schema = True

                tools[name] = ArrestToolsetTool(
                    toolset=self,
                    tool_def=ToolDefinition(
                        name=name,
                        description=description,
                        parameters_json_schema=handler_schema.tool_args.model_json_schema(),
                        strict=meta.strict,
                        return_schema=return_schema,
                        include_return_schema=include_return_schema,
                    ),
                    max_retries=tool_max_retries,
                    args_validator=cast(
                        SchemaValidator,
                        TypeAdapter(handler_schema.tool_args).validator,
                    ),
                    resource=resource,
                    handler=handler,
                )

        return tools

    async def call_tool(
        self,
        name: str,
        tool_args: dict[str, Any],
        ctx: RunContext[AgentDepsT],
        tool: ToolsetTool[AgentDepsT],
    ) -> Any:
        assert isinstance(tool, ArrestToolsetTool)

        # args_validator produces a real `ToolArgs[...]` instance, not a dict,
        # despite the base class's `dict[str, Any]` type hint.
        args = cast(Any, tool_args)
        path_kwargs = args.path_params.model_dump()
        request_data = args.request_body
        meta = tool.handler.tool_meta

        try:
            call = tool.resource.request(
                method=tool.handler.method,
                path=tool.handler.build_path(**path_kwargs),
                request=request_data,
            )
            response = await call
        except HandlerNotFound as exc:
            raise ToolFailed(str(exc)) from exc
        except RequestError as exc:
            raise ModelRetry(str(exc)) from exc
        except ArrestHTTPException as exc:
            message = f"{tool.handler.method} {tool.handler.route} failed with {exc.status_code}: {exc.data}"
            if exc.status_code in self._retry_on_errors:
                raise ModelRetry(message) from exc
            raise ToolFailed(message) from exc

        if isinstance(response, ArrestResponse):
            if not response.is_success:
                message = (
                    f"{tool.handler.method} {tool.handler.route} returned "
                    f"{response.status_code}: {response.data}"
                )
                if response.status_code in self._retry_on_errors:
                    raise ModelRetry(message)
                raise ToolFailed(message)
            return self._apply_truncation(response.data, meta)

        return self._apply_truncation(response, meta)

    def _apply_truncation(self, data: Any, meta: ToolMeta | None) -> Any:
        if meta is None or meta.max_items is None or not isinstance(data, list):
            return data
        if len(data) <= meta.max_items:
            return data

        if meta.on_truncate == "raise":
            raise ToolFailed(
                f"Result has {len(data)} items, which exceeds the maximum of "
                f"{meta.max_items}. Narrow your query and try again."
            )

        truncated = data[: meta.max_items]
        return {
            "items": truncated,
            "truncated": True,
            "total_items": len(data),
            "returned_items": len(truncated),
        }
