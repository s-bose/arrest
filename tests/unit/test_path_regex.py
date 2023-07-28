import re
import pytest
from contextlib import nullcontext as noraise

from arrest.resource import Resource


@pytest.mark.parametrize(
    "path, expected_regex, exception",
    [
        ("/posts", "^/posts$", noraise()),
        ("/posts/{post_id}", "^/posts/(?P<post_id>[^/]+)$", noraise()),
        ("/posts/{post_id:int}", "^/posts/(?P<post_id>[0-9]+)$", noraise()),
        (
            "/posts/{post_id:UUID}",
            "^/posts/(?P<post_id>[0-9]+)$",
            pytest.raises(AssertionError),
        ),
        (
            "/posts/{post_id:str}/comments/{comment_id:int}",
            "^/posts/(?P<post_id>[^/]+)/comments/(?P<comment_id>[0-9]+)$",
            noraise(),
        ),
        (
            "/posts/{post_id:str}/comments/{post_id:int}",
            "^/posts/(?P<post_id>[^/]+)/comments/(?P<comment_id>[0-9]+)$",
            pytest.raises(ValueError),
        ),
        (
            "https://www.httpie.org/users/{id}/post/{post_id}/comments",
            "^https://www\\.httpie\\.org/users/(?P<id>[^/]+)/post/(?P<post_id>[^/]+)/comments$",
            noraise(),
        ),
    ],
)
def test_compile_path_regex(path, expected_regex, exception):
    with exception:
        resource = Resource(name="foo", route="/bar")
        assert resource.compile_path(path) == re.compile(expected_regex)
