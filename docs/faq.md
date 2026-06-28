# Frequently Asked Questions

---

## Why does my response have `.data` instead of being the data directly?

Arrest wraps every HTTP response in a `Response[T]` object that bundles the parsed payload together with transport-level metadata. This gives you access to `response.status_code`, `response.raw` (the underlying `httpx.Response`), `response.elapsed`, and `response.url` — not just the payload.

```python
resp = await svc.users.get("/")
print(resp.data)        # the parsed/deserialized body
print(resp.status_code) # 200
print(resp.raw.headers) # raw httpx response headers
```

`Response[T]` is a frozen dataclass — treat it as read-only.

---

## How do I check if a request succeeded?

Use the convenience properties on the `Response` object:

```python
resp = await svc.users.get("/")

resp.is_success        # 200–299
resp.is_client_error   # 400–499
resp.is_server_error   # 500–599
resp.is_redirect       # 300–399
```

You can also inspect `resp.status_code` directly for fine-grained checks.

---

## How do I handle 404 or other errors?

Arrest returns a `Response` for **all** HTTP status codes — 404 included. Check `resp.status_code` or `resp.is_client_error`:

```python
resp = await svc.users.get("/999")
if resp.is_client_error:
    print(f"Not found: {resp.status_code}")
```

!!! note
    Only **transport-level** failures (timeout, connection refused, DNS errors) raise
    `RequestError`. A server responding with `500` still produces a normal `Response` object
    unless you set `raise_for_status=True`.

---

## How do I use path parameters?

Define them inside curly braces in your handler route, with an optional type:

```python
Resource(
    route="/user",
    handlers=[
        ("GET", "/{user_id}"),               # string by default
        ("GET", "/{user_id:uuid}"),          # UUID-typed
        ("GET", "/{user_id}/posts/{post_id:int}"),  # int-typed
    ]
)
```

Supply values with an f-string, a static string, or as keyword arguments:

```python
# f-string
await svc.user.get(f"/{user_id}")

# kwargs (Arrest fills unmatched path segments)
await svc.user.get("/", user_id=user_id)
await svc.user.get("/", user_id=user_id, post_id=10)
```

See [Configuring Requests](configuring-request.md#path-parameters) for full details, including how Arrest resolves multiple handlers with kwargs.

---

## Why am I getting `HandlerNotFound`?

`HandlerNotFound` means Arrest couldn't match your call to any registered handler. Common causes:

| Cause | Fix |
|---|---|
| **Method mismatch** | A handler is registered for `POST` but you called `.get()` |
| **Trailing slash mismatch** | `("/")` vs `("")` are different handlers — be consistent |
| **Path doesn't match** | The path you passed doesn't match any registered handler route |

!!! tip "Debugging tip"
    Print `your_resource.routes` to inspect registered handlers, or check that the HTTP method and route (including trailing slashes) match exactly.

---

## How do retries work?

Set `max_retries` in your `ArrestConfig`. Arrest uses [tenacity](https://github.com/jd/tenacity) with **randomized exponential backoff** (up to 60 seconds between attempts) and retries on `httpx.TimeoutException` and `httpx.RequestError`:

```python
from arrest import Service, Resource
from arrest._config import ArrestConfig

svc = Service(
    name="api",
    url="https://example.com",
    resources=[...],
    config=ArrestConfig(max_retries=3),
)
```

!!! note "Alternative: transport-level retries"
    You can also use `httpx.AsyncHTTPTransport(retries=3)` for transport-level retries. When both are set, Arrest's tenacity-based retries wrap around the transport-level ones — so they can compose, but be mindful of total attempt counts.

---

## What types can I use for request/response?

Arrest supports:

- **Pydantic models** (`BaseModel`) — full validation and serialization
- **Python dataclasses** — convert to/from dicts automatically
- **Plain `dict`** — sent as JSON with no extra validation
- **Lists** — `list[dict]`, `list[int]`, etc.
- **Primitives** — `str`, `int`, `float`, `bool`

```python
# All valid:
await svc.users.post("/", request=MyPydanticModel(...))
await svc.users.post("/", request={"name": "Alice"})
await svc.users.post("/", request=["a", "b", "c"])
```

See [Quickstart](quickstart.md) for more examples.

---

## Can I use arrest without async?

No — Arrest is async-only. It uses `httpx.AsyncClient` internally, so all calls must be `await`ed:

```python
# ✅ correct
resp = await svc.users.get("/")

# ❌ won't work
resp = svc.users.get("/")
```

If you need sync calls, wrap them with `asyncio.run()` at the top level, or use a sync wrapper in your application layer.

---

## How do I test code that uses arrest?

Use `httpx.ASGITransport` to route requests through a local ASGI app (like FastAPI or Starlette) without hitting a real network:

```python
import httpx
import pytest
from arrest import Service, Resource
from arrest._config import ArrestConfig

@pytest.fixture
async def client():
    # point at your FastAPI/Starlette app
    transport = httpx.ASGITransport(app=your_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

async def test_get_user(client):
    svc = Service(
        name="test",
        url="http://test",
        resources=[...],
        config=ArrestConfig(client=client),
    )
    resp = await svc.users.get("/1")
    assert resp.is_success
```

You can also use [respx](https://github.com/lundberg/respx) to mock at the HTTP layer without an ASGI app.

---

## How do I add custom headers/auth to every request?

Set `headers` or `auth` in `ArrestConfig` at any level — they merge according
to the hierarchy:

```
per-call kwargs  >  handler config  >  resource config  >  service config
```

```python
import httpx
from arrest._config import ArrestConfig

# Basic auth
svc = Service(
    name="api",
    url="https://example.com",
    config=ArrestConfig(
        headers={"x-api-key": "svc-level"},
        auth=httpx.BasicAuth(username="user", password="pass"),
    ),
    resources=[...],
)

# Bearer token
class BearerAuth(httpx.Auth):
    def __init__(self, token: str):
        self.token = token

    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request

svc = Service(
    name="api",
    url="https://example.com",
    config=ArrestConfig(auth=BearerAuth("my-token")),
    resources=[...],
)

# dict fields (headers, cookies, params) merge additively
# scalar fields (auth, timeout) override by highest non-None value
resp = await svc.users.get("/", headers={"x-trace": "abc"})
# headers sent: x-api-key + x-trace
```

!!! tip
    For per-handler headers, pass `headers` directly to the `ResourceHandler`. See [Configuring Requests](configuring-request.md) for more.
