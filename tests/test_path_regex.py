import re
from contextlib import nullcontext as noraise

import pytest

from arrest.converters import compile_path, get_converter


@pytest.mark.parametrize(
    "path, expected_regex, expected_path_format, expected_params, exception",
    [
        ("/posts", "^/posts$", "/posts", {}, noraise()),
        (
            "/posts/{post_id}",
            "^/posts/(?P<post_id>[^/]+)$",
            "/posts/{post_id}",
            {"post_id": get_converter("str")},
            noraise(),
        ),
        (
            "/posts/{post_id:int}",
            "^/posts/(?P<post_id>[0-9]+)$",
            "/posts/{post_id}",
            {"post_id": get_converter("int")},
            noraise(),
        ),
        (
            "/posts/{post_id:uuid}",
            "^/posts/(?P<post_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
            "/posts/{post_id}",
            {"post_id": get_converter("uuid")},
            noraise(),
        ),
        (
            "/posts/{post_id:UUID}",
            "^/posts/(?P<post_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
            "/posts/{post_id}",
            {"post_id": get_converter("uuid")},
            noraise(),
        ),
        (
            "/posts/{post_id:str}/comments/{comment_id:int}",
            "^/posts/(?P<post_id>[^/]+)/comments/(?P<comment_id>[0-9]+)$",
            "/posts/{post_id}/comments/{comment_id}",
            {"post_id": get_converter("str"), "comment_id": get_converter("int")},
            noraise(),
        ),
        (
            "/posts/{post_id:str}/comments/{post_id:int}",
            "^/posts/(?P<post_id>[^/]+)/comments/(?P<comment_id>[0-9]+)$",
            None,
            None,
            pytest.raises(ValueError),
        ),
        (
            "https://www.httpie.org/users/{id}/post/{post_id}/comments",
            "^https://www\\.httpie\\.org/users/(?P<id>[^/]+)/post/(?P<post_id>[^/]+)/comments$",
            "https://www.httpie.org/users/{id}/post/{post_id}/comments",
            {"id": get_converter("str"), "post_id": get_converter("str")},
            noraise(),
        ),
    ],
)
def test_compile_path(path, expected_regex, expected_path_format, expected_params, exception):
    with exception:
        assert compile_path(path) == (
            re.compile(expected_regex),
            expected_path_format,
            expected_params,
        )
