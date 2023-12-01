# Getting Started

Assuming you already have arrest installed in your system, let us create a simple connection.
We have a REST endpoint `http://example.com/api/v1` which has a resource `/user` with method `GET`

```python

from arrest import Service, Resource

example_svc = Service(
    name="example",
    url="http://example.com/api/v1",
    resources=[
        Resource(
            name="user",
            route="/user",
            handlers=[
                ("GET", "/")
            ]
        )
    ]
)
```

Now that our service is defined, we can proceed to use it elsewhere.

```python

await example_svc.user.get("/")
```

If we want to enable exception handling, simply import `ArrestHTTPException`, or more generic `ArrestError`

```python
from arrest.exceptions import ArrestHTTPException

try:
    resp = await example_svc.user.get("/")
except ArrestHTTPException as exc:
    print(f"{exc.status_code} {exc.data}")

return resp
```
