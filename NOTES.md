1. if the resource contains only one handler and that handler url contains multiple path params like this:

```python
Resource(
    route="/user",
    handlers=[
        (Methods.POST, "/profile/{id:int}/comments/{comment_id:int}"),
    ],
)
```

then you can pass all the path_params as kwargs in the request by specifying the url as `/user`

```python
user.post("/profile", id=123, comment_id=456)
user.post("/profile/123", comment_id=456)
user.post("/profile/123/comments", comment_id=456)
user.post("/profile/123/comments/456")
```

all 4 would work

2. However if it contains specific paths from `/profile`, then you need to specify the sub-resource name of the specific `profile` with a trailing slash

```python
Resource(
    route="/user",
    handlers=[
        (Methods.POST, "/profile/{id:int}"),
        (Methods.POST, "/profile/{id:int}/comments/{comment_id:int}"),
    ],
)

user.post("/profile", id=123, comments=456) # wont work
user.post("/profile/123/comments/", comments=456) # will work
```


# TODO: disallow addition of conflicting handlers
