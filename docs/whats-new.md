# What's New

This page highlights the most important changes in the latest release of Arrest,
ordered by priority and impact.

---

## 1. Unified `Response[T]` — a single response type for success and error paths

**Breaking change** — Arrest now returns a `Response[T]` for **every** HTTP status code,
not just 2xx. Transport-level failures (timeouts, connection errors) still raise
`ArrestHTTPException`, but a server returning `404`, `500`, or any other status
now produces a normal `Response` object you can inspect.

Previously you had to `try/except ArrestHTTPException` for non-2xx responses.
Now you check properties on the response itself:

```python
resp = await svc.users.get("/999")

if resp.is_client_error:
    print(f"Not found: {resp.status_code}, body: {resp.data}")

if resp.is_server_error:
    print(f"Server error: {resp.data}")

if resp.is_success:
    user: UserResponse = resp.data  # type-safe access
```

**Convenience properties on `Response[T]`:**

| Property | Range |
|---|---|
| `is_success` | 200–299 |
| `is_redirect` | 300–399 |
| `is_client_error` | 400–499 |
| `is_server_error` | 500–599 |

Every `Response[T]` also carries:

| Field | Description |
|---|---|
| `data` | The parsed/deserialized body (`T`) |
| `status_code` | HTTP status code (`int`) |
| `url` | Final request URL (`httpx.URL`) |
| `elapsed` | Time taken for the response (`timedelta \| None`) |
| `raw` | The underlying `httpx.Response` |
| `request` | The `httpx.Request` that was sent |

**Migration guide:**

```python
# before (v0.1.x) — exceptions for non-2xx
try:
    resp = await svc.users.get("/123")
    print(resp.data)
except ArrestHTTPException as exc:
    print(f"Error: {exc.status_code} — {exc.data}")

# after (latest) — Response for all status codes
resp = await svc.users.get("/123")
if resp.is_success:
    print(resp.data)
else:
    print(f"Error: {resp.status_code} — {resp.data}")
```

---

## 2. `H()` helper — type-safe handler definitions

Defining handlers with raw tuples `("GET", "/", Request, Response)` works but
gives no IDE autocomplete and it's easy to forget the positional order.
The new `H()` helper gives you keyword-argument clarity and full type-checking:

```python
from arrest import H, Resource, GET, POST

user_resource = Resource(
    name="users",
    route="/users",
    handlers=[
        H(GET, "/"),
        H(POST, "/", request=NewUserRequest, response=UserResponse),
        H(GET, "/{user_id:str}", response=UserResponse, headers={"x-custom": "value"}),
    ],
)
```

`H()` accepts all the same fields as `ResourceHandler`:

```python
def H(
    method: Methods,
    route: str,
    request: Any = None,
    response: Any = None,
    callback: Callable | None = None,
    *,
    headers: dict[str, str] | None = None,
) -> ResourceHandler: ...
```

The old tuple/dict syntax still works, so existing code won't break.

---

## 3. Form and File primitives for `multipart/form-data` and `application/x-www-form-urlencoded`

Arrest now supports form-encoded and multipart requests via two new field annotations:
`Form(...)` and `File(...)` (imported from `arrest.params`).

### Form fields (`application/x-www-form-urlencoded`)

```python
from pydantic import BaseModel
from arrest import Resource, Service
from arrest.params import Form

class LoginRequest(BaseModel):
    username: str = Form(...)
    password: str = Form(...)

auth_resource = Resource(
    route="/auth",
    handlers=[
        ("POST", "/login", LoginRequest),
    ],
)

await svc.auth.post("/login", request=LoginRequest(username="alice", password="s3cret"))
# Content-Type: application/x-www-form-urlencoded
# Body: username=alice&password=s3cret
```

### File uploads (`multipart/form-data`)

```python
from arrest.params import File, Form
from arrest.types import UploadFile

class ProfileUpdate(BaseModel):
    display_name: str = Form(...)
    avatar: UploadFile = File(...)

# Upload from disk
with open("avatar.png", "rb") as f:
    avatar = UploadFile(filename="avatar.png", content_type="image/png", file=f)
    await svc.user.post("/profile", request=ProfileUpdate(
        display_name="Alice",
        avatar=avatar,
    ))

# Upload raw bytes
await svc.user.post("/profile", request=ProfileUpdate(
    display_name="Alice",
    avatar=b"raw image bytes...",
))
```

!!! warning "Cannot mix JSON and Form"
    A single request model cannot mix `Body()` (or unannotated) fields with
    `Form()` / `File()` fields. Arrest will raise a `ValueError`.

---

## 4. Documentation provider: MkDocs → Zensical

The documentation site has been migrated from **MkDocs** (with Material theme)
to **[Zensical](https://github.com/s-bose/zensical)** — a modern, fast
documentation generator written in Rust.

- Faster build times
- Built-in search, code copy, and navigation features
- Same Material-style look with accent color and light/dark palette
- Configuration is now in `zensical.toml` at the project root

If you're contributing doc changes, use `zensical serve` instead of `mkdocs serve`.

---

## 5. Package manager: Poetry → uv

The project now uses **[uv](https://github.com/astral-sh/uv)** as its package
manager instead of Poetry.

| Area | Before (Poetry) | After (uv) |
|---|---|---|
| Dependency file | `pyproject.toml` + `poetry.lock` | `pyproject.toml` + `uv.lock` |
| Build backend | `poetry.core` | `hatchling` |
| Install | `poetry add arrest` | `uv add arrest` |
| Dev setup | `poetry install --with dev,test,docs` | `uv sync --group dev --group test --group docs` |

The `pyproject.toml` now uses [PEP 735](https://peps.python.org/pep-0735/)
dependency groups (`[dependency-groups]`) for organizing optional dependencies.

---

## See also

- [Getting Started](getting-started.md) — detailed walkthrough of `H()`, `Response[T]`, and `Form`/`File`
- [Configuring your request](configuring-request.md) — full reference for request parameters
- [FAQ](faq.md) — common questions about using `Response[T]`
- [Release Notes](release-notes.md) — full changelog
