import pytest
from pydantic import BaseModel

from arrest.utils import extract_model_field, join_url, extract_resource_and_suffix


class MyModel(BaseModel):
    a: str
    b: str
    c: int


def test_extract_model_field():
    dct = extract_model_field(model=MyModel(a="a", b="b", c=123), field="c")
    assert dct == {"c": 123}

    dct = extract_model_field(model=MyModel(a="a", b="b", c=123), field="b")
    assert dct == {"b": "b"}

    dct = extract_model_field(model=MyModel(a="a", b="b", c=123), field="d")
    assert dct == {}


@pytest.mark.parametrize(
    argnames="parts, url",
    argvalues=[
        (["/abc"], "/abc"),
        (["/abc", "/def"], "/abc/def"),
        (["/abc/def/"], "/abc/def/"),
        (["/abc", "/{uuid}"], "/abc/{uuid}"),
        (["/abc", ""], "/abc"),
        (["/abc", "/"], "/abc/"),
        (["/"], "/"),
        ([""], ""),
    ],
)
def test_join_url(parts: list[str], url: str):
    base_url: str = "/root"
    assert f"{base_url}{url}" == join_url(base_url, *parts)


@pytest.mark.parametrize(
    argnames="path, resource, suffix",
    argvalues=[
        ("/abc", "abc", ""),
        ("/abc/", "abc", "/"),
        ("/abc/def", "abc", "/def"),
        ("/abc/def/", "abc", "/def/"),
        ("/abc/{uuid}", "abc", "/{uuid}"),
        ("", "", ""),
        ("/", "", "/"),
    ],
)
def test_extract_resource_and_suffix(path: str, resource: str, suffix: str):
    res, suf = extract_resource_and_suffix(path=path)
    assert resource == res
    assert suffix == suf
