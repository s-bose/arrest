# AI Toolset

Arrest can expose any arrest service as a set of tools for an AI agent to call, via
[`pydantic-ai`](https://ai.pydantic.dev/)'s [`AbstractToolset`](https://ai.pydantic.dev/toolsets/)
interface.

Instead of hand-writing a tool function per endpoint, along with its
JSON schema, error handling, and HTTP plumbing, you point `ArrestToolset` at
a `Service` you've already defined and opt individual handlers in with
`tool_meta`. Arrest derives the tool's name, description, argument schema,
and return schema from the handler definition, and dispatches calls through
the same `Resource`/`ResourceHandler` machinery used everywhere else in
Arrest.

!!! Note
    This feature depends on `pydantic-ai`, which is not a default dependency
    of Arrest.

    ```bash
    pip install "arrest[ai]"

    uv add arrest --extra ai
    ```

## Opting a handler in with `ToolMeta`

By default, no handler is exposed as a tool. A handler only becomes visible
to `ArrestToolset` once it carries `tool_meta`, set via `H(..., tool_meta=ToolMeta(...))`:

```python
from arrest import GET, POST, H, Resource
from arrest.ai.meta import ToolMeta

users = Resource(
    name="users",
    route="/users",
    handlers=[
        H(
            GET,
            "/{user_id}",
            None,
            User,
            tool_meta=ToolMeta(
                name="get_user_by_id",
                description="Get a single user by their id.",
            ),
        ),
        H(
            POST,
            "/",
            UserCreate,
            User,
            tool_meta=ToolMeta(name="create_user", description="Create a new user."),
        ),
        # no tool_meta => this handler is never registered as a tool
        H(GET, "/all", None, None),
    ],
)
```

`ToolMeta` fields:

| field | default | purpose |
| --- | --- | --- |
| `name` | `None` | overrides the auto-generated tool name |
| `description` | `None` | overrides the auto-generated tool description |
| `include` | `True` | set to `False` to keep `tool_meta` on a handler without exposing it as a tool |
| `strict` | `None` | pydantic-ai strict schema mode for this tool |
| `metadata` | `None` | free-form dict, reserved for future use |
| `max_items` | `None` | see [Result truncation](#result-truncation) |
| `on_truncate` | `"note"` | `"note"` or `"raise"`, see [Result truncation](#result-truncation) |

When `name` is omitted, Arrest derives one from the resource, method, and
route (e.g. `GET /{user_id}` on resource `users` becomes
`get_users_user_id`). When `description` is omitted, it falls back to
`"{METHOD} {route} on the '{resource}' resource"`.

Handlers whose request or response type can't be represented as a JSON
schema, such as multipart bodies (`File()`/`Form()` fields) and XML bodies
(`BaseXmlModel`), are silently skipped even if they carry `tool_meta`, since
there is no JSON-schema shape an LLM tool call can fill in for them.

## `ArrestToolset`

```python
from arrest.ai.toolset import ArrestToolset
from pydantic_ai import Agent

toolset = ArrestToolset(service)
agent = Agent(model="anthropic:claude-haiku-4-5", toolsets=[toolset])

result = await agent.run("Get a random user, then list every task belonging to that user.")
print(result.output)
```

Each handler with `tool_meta` becomes one pydantic-ai tool, callable by
name. Path parameters and the request body are exposed to the model as a
single JSON schema (see [Argument schema](#argument-schema-toolargs)); if the
handler declares a `response` type, its schema is attached too so the model
knows the shape of what it gets back.

### Constructor options

```python
ArrestToolset(
    service,
    id=None,
    include=None,
    exclude=None,
    tool_max_retries=None,
    config=None,
    retry_on_errors=None,
)
```

`id` is the toolset's id, defaulting to a sanitized
`arrest-{service.name}-service`. `include` and `exclude` give fine-grained
filtering on top of `tool_meta`, covered in
[Selective exposure](#selective-exposure-includeexclude) below.
`tool_max_retries` overrides pydantic-ai's default per-tool retry count,
falling back to the run's `max_retries` when unset. `config` is an
`ArrestConfig` merged over every resource's own config for the lifetime of
the toolset, see [Pooled client](#pooled-client) below. `retry_on_errors` is
the set of HTTP status codes that should trigger a `ModelRetry` instead of a
hard `ToolFailed`, defaulting to `{408, 429, 500, 502, 503, 504}`.

### Pooled client

`ArrestToolset` is an async context manager, implementing `__aenter__`/`__aexit__`:

```python
async with ArrestToolset(service) as toolset:
    ...
```

On `__aenter__`, if `config` didn't already supply an `httpx.AsyncClient`,
the toolset opens one pooled `httpx.AsyncClient` (bound to the service's
`url`) and shares it across every request the toolset makes for the
lifetime of the toolset, instead of each call opening and closing its
own client. The effective config (the pooled client, plus anything
passed via `config`) is merged into every resource in the service on
entry, and each resource's original config is restored on exit, so
using a service inside a toolset does not permanently mutate it.

You don't normally need to call this yourself. `Agent(toolsets=[toolset])`
already enters and exits every toolset for the duration of each
`agent.run(...)` call, so just pass the toolset to the agent and call
`run()`; no `async with` needed, as in the examples above. Enter it
manually only if you're calling `ArrestToolset.get_tools()`/`call_tool()`
directly, outside of pydantic-ai's own run lifecycle.

!!! note "Config merge order"
    The toolset's `config` is layered *on top of* each resource's existing
    config (non-`None` fields in `config` win), and the result replaces that
    resource's config for the toolset's lifetime. This sits above Arrest's
    normal per-call kwargs > handler config > resource config > service
    config chain, since `call_tool` dispatches with no per-call or
    handler-level config of its own — so in practice, `ArrestToolset(...,
    config=...)` is the highest-priority config in effect while the toolset
    is open.

### Tool building is lazy and cached

Tools are built once, on the first `get_tools()` call for a run, via
`_build_tools()`, and then cached on the toolset instance. Registering a
`tool_meta` with a `name` that collides with another handler's generated or
explicit name raises `UserError` at build time; disambiguate with
`tool_meta.name`.

## Selective exposure: `include`/`exclude`

`include` and `exclude` narrow the set of handlers exposed as tools, on top
of the `tool_meta` opt-in. Both accept the same three shapes, of increasing
granularity:

```python
# only expose whole resources
{"users", "tasks"}

# only expose specific methods on a resource
{"users": {"GET", "POST"}}

# only expose specific routes for a given method on a resource
{"users": {"GET": {"/{user_id}", "/all"}}}
```

`exclude` is applied after `include`, so a handler must pass both checks:
match (or not be restricted by) `include`, and not match `exclude`.

```python
# expose every users/tasks tool_meta-tagged handler except deletes
toolset = ArrestToolset(
    service,
    include={"users", "tasks"},
    exclude={"users": {"DELETE"}, "tasks": {"DELETE"}},
)
```

## Argument schema (`ToolArgs`)

For every exposed handler, `arrest.ai.schema.build_args_model` derives a
`ToolArgs[PathParamsT, RequestBodyT]` pydantic model:

```python
class ToolArgs(BaseModel, Generic[PathParamsT, RequestBodyT]):
    path_params: PathParamsT
    request_body: RequestBodyT
```

- `path_params` is a dynamically generated model with one field per
  `{name:converter}` placeholder in the handler's route (e.g. a route of
  `/{user_id:str}/posts/{post_id:uuid}` produces a model with a `str`
  `user_id` field and a `UUID` `post_id` field).
- `request_body` is the handler's own `request` type, used as-is.

This combined model is what the model actually fills in when it calls the
tool, and what pydantic-core validates the call's arguments against.

## Request dispatch

`call_tool` never re-resolves the model's arguments against the service's
route table. It dispatches directly against the exact `ResourceHandler` the
tool was built from. Path parameters are substituted into a concrete path via
`ResourceHandler.build_path(**path_params)`, and the resulting request is
made through that handler's owning `Resource`. This avoids the ambiguity
between overlapping route templates (e.g. `/{id}` vs. `/{id}/tasks`) that a
runtime route-matching approach would otherwise have to resolve.

Errors are translated into pydantic-ai's tool-failure vocabulary:

| Arrest condition | pydantic-ai outcome |
| --- | --- |
| `HandlerNotFound` | `ToolFailed` |
| transport-level `RequestError` (network failure, timeout, etc.) | `ModelRetry` |
| HTTP error response, status in `retry_on_errors` | `ModelRetry` |
| HTTP error response, status not in `retry_on_errors` | `ToolFailed` |

`ModelRetry` gives the model a chance to correct itself and try again (up to
`tool_max_retries`); `ToolFailed` ends the tool call as a hard failure.

!!! warning "Don't stack Arrest retries with tool retries"
    `retry_on_errors`/`tool_max_retries` are pydantic-ai's model-level retry —
    the agent sees the failure and decides whether to call the tool again.
    Arrest's own transport retry (`ArrestConfig.max_retries`, tenacity-based)
    and `raise_for_status` operate independently, underneath that. If a
    resource is also configured with `max_retries`, a single tool call can
    retry silently at the transport layer *and then* trigger a `ModelRetry`
    on top, compounding delay and retry counts. Pick one layer to own
    retries for tool-exposed handlers — usually the toolset's, since it's
    the one the model can reason about — and leave the other unset.

## Result truncation

If `ToolMeta.max_items` is set and the handler's result is a `list` longer
than that, the toolset intervenes before the result reaches the model. By
default (`on_truncate="note"`), it returns a truncated payload annotated
with truncation metadata. Set `on_truncate="raise"` instead to have it raise
`ToolFailed` with a message telling the model to narrow its query, rather
than returning a huge payload:

```python
{
    "items": [...],       # first `max_items` items
    "truncated": True,
    "total_items": 137,
    "returned_items": 20,
}
```

```python
H(
    GET,
    "/all",
    None,
    None,
    tool_meta=ToolMeta(
        name="list_tasks",
        description="List every task.",
        max_items=20,
        on_truncate="raise",
    ),
)
```

Truncation only applies to `list` results. Scalar or object responses are
returned as-is regardless of `max_items`.

## Full example

```python
from arrest import GET, POST, H, Resource, Service
from arrest.ai.meta import ToolMeta
from arrest.ai.toolset import ArrestToolset
from pydantic_ai import Agent

users = Resource(
    name="users",
    route="/users",
    handlers=[
        H(GET, "/{user_id}", None, User, tool_meta=ToolMeta(name="get_user_by_id")),
        H(GET, "/all", None, None, tool_meta=ToolMeta(name="list_users", max_items=20)),
        H(POST, "/", UserCreate, User, tool_meta=ToolMeta(name="create_user")),
    ],
)

service = Service(name="example", url="http://localhost:8080/api", resources=[users])

toolset = ArrestToolset(service, retry_on_errors=[429, 503])
agent = Agent(model="anthropic:claude-haiku-4-5", toolsets=[toolset])

result = await agent.run("Look up the user with id abc123.")
print(result.output)
```

For more info, check the [API Documentation](api.md).
