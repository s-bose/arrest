import re
from typing import Any, Callable, NamedTuple, Pattern, overload

from pydantic import BaseModel, ConfigDict, PrivateAttr
from arrest.ai.meta import ToolMeta

from arrest.converters import replace_params
from arrest.exceptions import ConversionError
from arrest.http import Methods
from arrest.logging import logger


class HandlerKey(NamedTuple):
    method: Methods
    route: str


class ResourceHandler(BaseModel):
    """
    A pydantic class defining a resource handler

    Parameters:
        method (Methods):
            HTTP Method for the handler
        route (str):
            Unique path to the handler from its parent resource
        request (T, optional):
            Python type to validate the request with
        response (T, optional):
            Python type to deserialize the HTTP response
        callback (Callable, optional):
            A callable (sync or async) to execute with the HTTP
            response
        headers (dict, optional):
            default Headers for the handlers, can be overridden
            by runtime headers
        tool_meta: (ToolMeta, optional):
            optional metadata for tool definitions, used during tool
            registration
    """

    model_config = ConfigDict(extra="forbid")

    method: Methods
    route: str
    request: Any | None = None
    response: Any | None = None
    callback: Callable | None = None
    headers: dict[str, str] | None = None
    tool_meta: ToolMeta | None = None

    _path_format: str | None = PrivateAttr(default=None)
    _path_regex: Pattern | None = PrivateAttr(default=None)
    _param_types: Any = PrivateAttr(default=None)

    def build_path(self, **path_params: Any) -> str:
        """Build the concrete path for this handler by substituting
        `path_params` into its route template, e.g. for a handler bound to
        `/{user_id}/tasks`, `build_path(user_id="abc")` returns `/abc/tasks`.

        Returns:
            str:
                The concrete path with all placeholders substituted with

        Raises:
            RuntimeError:
                If the handler has not been bound to a resource yet, and thus
                has no compiled path format available.
            ValueError:
                If any placeholders in the route template are not provided in
                `path_params`.
        """
        if self._path_format is None or self._param_types is None:
            raise RuntimeError(
                f"Handler {self.method} {self.route!r} has not been bound to "
                "a resource yet; no compiled path format available."
            )

        path, remaining = replace_params(
            path=self._path_format,
            path_params=dict(path_params),
            param_types=self._param_types,
        )
        if remaining:
            raise ValueError(
                f"Unresolved path params {list(remaining)} for handler "
                f"{self.method} {self.route!r}"
            )
        return path

    def match(self, method: Methods, path: str, **kwargs) -> tuple[str, int] | None:
        """Resolve `path` (plus `kwargs`) against this handler's route.
        `Resource.get_matching_handler` uses the returned extension to pick
        the closest match when routes overlap as prefixes of each other,
        e.g. `/{id}` vs `/{id}/tasks`.

        Parameters:
            method (Methods):
                HTTP method the request was made with
            path (str):
                Path to match, e.g. `/{id}/tasks` or a concrete path
            **kwargs:
                Values for any route placeholders `path` doesn't cover

        Returns:
            tuple[str, int] | None:
                `(path, extension)` if `path` and `kwargs` together resolve
                this handler's route, else `None`. `extension` counts
                template segments past `path` that had to come from
                `kwargs` (0 for an exact match).
        """
        if method != self.method:
            return None

        if kwargs:
            return self.__resolve_path_param(path, **kwargs)

        parsed = self.__parse_exact_path(path)
        return (parsed, 0) if parsed is not None else None

    def __parse_exact_path(self, path: str) -> str | None:
        if not self._path_regex:
            return None
        if self._path_regex.fullmatch(path):
            return path

    def __resolve_path_param(self, path: str, **kwargs) -> tuple[str, int] | None:
        extracted = self.__extract_path_params(path)
        if extracted is None:
            return None
        path_format, params, extension = extracted
        params |= kwargs

        try:
            parsed_path, remaining_params = replace_params(
                path=path_format,
                path_params=params,
                param_types=self._param_types,
            )
        except ConversionError as exc:
            logger.warning(str(exc), exc_info=True)
            return None
        if remaining_params:
            return None

        final = self.__parse_exact_path(parsed_path)
        return (final, extension) if final is not None else None

    def __extract_path_params(self, path: str) -> tuple[str, dict, int] | None:
        """Positionally match `path`'s segments as a literal prefix of this
        handler's own template. A template placeholder at a position where
        `path` supplies a value fills that param; a template placeholder
        beyond `path`'s length is left for `kwargs` to fill instead (this is
        what lets a short hint path like "/posts" discover a longer nested
        route via kwargs). Returns `(path_format, params, extension)`, where
        `extension` is how many template segments past `path`'s own length
        remain."""
        if self._path_format is None:
            return None

        path_segments = path.split("/")
        template_segments = self._path_format.split("/")
        if len(path_segments) > len(template_segments):
            return None

        params: dict[str, str] = {}
        for path_seg, tmpl_seg in zip(path_segments, template_segments):
            if placeholder := re.match(r"^{(\w+)}$", tmpl_seg):
                if path_seg:
                    params[placeholder.group(1)] = path_seg
            elif path_seg != tmpl_seg:
                return None

        return self._path_format, params, len(template_segments) - len(path_segments)


@overload
def H(
    method: Methods,
    route: str,
    *,
    headers: dict[str, str] | None = None,
    tool_meta: ToolMeta | None = None,
) -> ResourceHandler: ...
@overload
def H(
    method: Methods,
    route: str,
    request: Any,
    *,
    headers: dict[str, str] | None = None,
    tool_meta: ToolMeta | None = None,
) -> ResourceHandler: ...
@overload
def H(
    method: Methods,
    route: str,
    request: Any,
    response: Any,
    *,
    headers: dict[str, str] | None = None,
    tool_meta: ToolMeta | None = None,
) -> ResourceHandler: ...
@overload
def H(
    method: Methods,
    route: str,
    request: Any,
    response: Any,
    callback: Callable[..., Any],
    *,
    headers: dict[str, str] | None = None,
    tool_meta: ToolMeta | None = None,
) -> ResourceHandler: ...


def H(
    method: Methods,
    route: str,
    request: Any = None,
    response: Any = None,
    callback: Callable[..., Any] | None = None,
    *,
    headers: dict[str, str] | None = None,
    tool_meta: ToolMeta | None = None,
) -> ResourceHandler:
    return ResourceHandler(
        method=method,
        route=route,
        request=request,
        response=response,
        callback=callback,
        headers=headers,
        tool_meta=tool_meta,
    )
