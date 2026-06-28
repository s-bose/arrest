# Migration Guide

This page catalogs every user-facing API change in v0.2.0, with side-by-side
before/after examples.

---

## Service & Resource construction

All httpx and Arrest settings that were previously scattered as kwargs on `Service`
and `Resource` now live in an `ArrestConfig` instance passed via `config=`.

=== "Before (v0.1.x)"

    ```python
    from arrest import Service, Resource
    import httpx

    svc = Service(
        name="api",
        url="https://example.com",
        headers={"x-api-key": "sk-123"},
        cookies={"session": "abc"},
        timeout=30.0,
        max_retries=3,
        follow_redirects=True,
        auth=("user", "pass"),
        transport=httpx.AsyncHTTPTransport(retries=2),
        verify=False,
    )

    user = Resource(
        route="/users",
        handlers=[("GET", "/")],
        headers={"x-org": "acme"},
        cookies={"env": "prod"},
        timeout=60.0,
    )
    ```

=== "After (v0.2.x)"

    ```python
    from arrest import Service, Resource
    from arrest._config import ArrestConfig
    import httpx

    svc = Service(
        name="api",
        url="https://example.com",
        config=ArrestConfig(
            headers={"x-api-key": "sk-123"},
            cookies={"session": "abc"},
            timeout=30.0,
            max_retries=3,
            follow_redirects=True,
            auth=httpx.BasicAuth(username="user", password="pass"),
            transport=httpx.AsyncHTTPTransport(retries=2),
            verify=False,
        ),
    )

    user = Resource(
        route="/users",
        handlers=[("GET", "/")],
        config=ArrestConfig(
            headers={"x-org": "acme"},
            cookies={"env": "prod"},
            timeout=60.0,
        ),
    )
    ```

---

## `add_resource` config overrides

=== "Before (v0.1.x)"

    ```python
    svc.add_resource(
        user_resource,
        timeout=120,
        headers={"x-extra": "val"},
        max_retries=5,
    )
    ```

=== "After (v0.2.x)"

    ```python
    # Set overrides on the Resource before adding.
    # Service config merges with Resource config automatically.
    from arrest._config import ArrestConfig

    user_resource = Resource(
        route="/users",
        handlers=[...],
        config=ArrestConfig(timeout=120, headers={"x-extra": "val"}, max_retries=5),
    )
    svc.add_resource(user_resource)
    ```

!!! tip "Why?"
    Keeping config on the Resource makes ownership clear — Service is a registrar,
    not a config overrider.

---

## Custom httpx client

=== "Before (v0.1.x)"

    ```python
    client = httpx.AsyncClient(transport=..., base_url="...")

    # Option A: on Service
    svc = Service(..., client=client)

    # Option B: on Resource
    user = Resource(..., client=client)
    ```

=== "After (v0.2.x)"

    ```python
    from arrest._config import ArrestConfig

    client = httpx.AsyncClient(transport=..., base_url="...")

    # Option A: on Service
    svc = Service(..., config=ArrestConfig(client=client))

    # Option B: on Resource
    user = Resource(..., config=ArrestConfig(client=client))
    ```

---

## Per-request overrides (unchanged)

The per-call API on `resource.request()` / `.get()` / `.post()` etc. is unchanged:

```python
# Still works as before
await svc.users.get("/", headers={"x-trace": "abc"})
await svc.users.post("/", request=payload, timeout=10)
await svc.users.request(method="GET", path="/", raise_for_status=True)
```

---

## `self.httpx_args` in custom handlers

The `Resource.httpx_args` convenience property is preserved for custom handlers:

```python
@svc.user.handler("/posts")
async def get_posts(self, url, *, post_id: int):
    async with httpx.AsyncClient(**self.httpx_args) as client:
        resp = await client.get(f"{url}/{post_id}")
    return resp.json()
```

It now delegates to `self.config.httpx_args()`.

---

## `H()` helper for handler definitions

Use `H()` instead of raw tuples or `ResourceHandler` for better IDE support and
explicit keyword arguments.

=== "Before (v0.1.x)"

    ```python
    from arrest import Resource, GET, POST
    from arrest.handler import ResourceHandler

    user = Resource(
        route="/users",
        handlers=[
            (GET, "/"),
            (POST, "/", NewUserRequest, UserResponse),
            ResourceHandler(
                method=GET,
                route="/{user_id}",
                response=UserResponse,
                headers={"x-custom": "val"},
            ),
        ],
    )
    ```

=== "After (v0.2.x)"

    ```python
    from arrest import H, Resource, GET, POST

    user = Resource(
        route="/users",
        handlers=[
            H(GET, "/"),
            H(POST, "/", request=NewUserRequest, response=UserResponse),
            H(GET, "/{user_id}", response=UserResponse, headers={"x-custom": "val"}),
        ],
    )
    ```

!!! tip "Prefer `H()`"
    Direct use of `ResourceHandler` is discouraged. `H()` gives you autocomplete,
    keyword-argument clarity, and the same validation.

---

## Unified `Response[T]` — success and error paths

Non-2xx responses now return a `Response` object instead of raising
`ArrestHTTPException`. Transport failures (timeout, DNS, connection refused)
raise `RequestError`.

=== "Before (v0.1.x)"

    ```python
    from arrest.exceptions import ArrestHTTPException

    try:
        resp = await svc.users.get("/999")
        user = resp.data  # only reached on 2xx
    except ArrestHTTPException as exc:
        # caught on 4xx, 5xx, AND transport errors
        print(f"Error: {exc.status_code} — {exc.data}")
    ```

=== "After (v0.2.x)"

    ```python
    from arrest.exceptions import RequestError

    try:
        resp = await svc.users.get("/999")
        if resp.is_success:
            user = resp.data
        elif resp.is_client_error:
            print(f"Not found: {resp.status_code} — {resp.data}")
    except RequestError as exc:
        # only transport failures (timeout, DNS, connection refused)
        print(f"Request failed: {exc.message}")
    ```

**Opt-in legacy behaviour** — set `raise_for_status=True` to raise `ArrestHTTPException`
on non-2xx:

```python
from arrest._config import ArrestConfig

svc = Service(..., config=ArrestConfig(raise_for_status=True))

# Now non-2xx raises ArrestHTTPException (with real status_code + data)
try:
    resp = await svc.users.get("/999")
except ArrestHTTPException as exc:
    print(exc.status_code, exc.data)
```

---

## Response inspection properties

Use the convenience properties on `Response[T]` instead of manual status-code checks:

=== "Before (v0.1.x)"

    ```python
    from arrest.exceptions import ArrestHTTPException

    try:
        resp = await svc.users.get("/123")
        # only 2xx reaches here
        print("success")
    except ArrestHTTPException as exc:
        if 400 <= exc.status_code < 500:
            print("client error")
        elif 500 <= exc.status_code < 600:
            print("server error")
    ```

=== "After (v0.2.x)"

    ```python
    from arrest.exceptions import RequestError

    try:
        resp = await svc.users.get("/123")
    except RequestError:
        print("transport failure")
    else:
        if resp.is_success:        # 200–299
            print("success")
        elif resp.is_redirect:     # 300–399
            print("redirect")
        elif resp.is_client_error: # 400–499
            print("client error")
        elif resp.is_server_error: # 500–599
            print("server error")
    ```

| Property | Range |
|---|---|
| `resp.is_success` | 200–299 |
| `resp.is_redirect` | 300–399 |
| `resp.is_client_error` | 400–499 |
| `resp.is_server_error` | 500–599 |

---

## Exception changes

=== "Before (v0.1.x)"

    ```python
    from arrest.exceptions import ArrestHTTPException

    try:
        resp = await svc.users.get("/123")
    except ArrestHTTPException as exc:
        # raised on non-2xx AND transport errors
        print(exc.status_code, exc.data)
    ```

=== "After (v0.2.x)"

    ```python
    from arrest.exceptions import RequestError
    try:
        resp = await svc.users.get("/123")
    except RequestError as exc:
        # transport failures only (timeout, DNS, connection refused)
        print(exc.message)

    # Non-2xx responses are Response objects by default
    if resp.is_client_error:
        print(resp.status_code, resp.data)

    # Or opt-in to legacy exception-on-error
    svc = Service(..., config=ArrestConfig(raise_for_status=True))
    ```
