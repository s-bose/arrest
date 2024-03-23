import enum
import typing
from dataclasses import dataclass

import pytest
from pydantic import BaseModel

try:
    from pydantic import RootModel
except ImportError:
    pass

from arrest._config import PYDANTIC_V2
from arrest.utils import (
    extract_model_field,
    extract_resource_and_suffix,
    join_url,
    jsonable_encoder,
    validate_model,
)


class MyModel(BaseModel):
    a: str
    b: str
    c: int


@dataclass
class MyModelDC:
    a: str
    b: str
    c: int


class MyEnum(str, enum.Enum):
    field = "field"


if PYDANTIC_V2:

    class MyModelRoot(RootModel):
        root: list[MyModel]

else:

    class MyModelRoot(BaseModel):
        __root__: list[MyModel]


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


@pytest.mark.parametrize(
    argnames="type_, obj, new_type, member_type",
    argvalues=[
        (str, "abc", str, None),
        (int, 123, int, None),
        (float, 123.4, float, None),
        (MyEnum, "field", str, None),
        (MyEnum, MyEnum.field, str, None),
        (list[int], [1, 2, 3], list, int),
        (list[MyEnum], ["field"], list, str),
        (MyModel, {"a": "a", "b": "b", "c": 123}, dict, str),
        (MyModel, MyModel(a="a", b="b", c=123), dict, str),
        (list[MyModel], [{"a": "a", "b": "b", "c": 123}, {"a": "A", "b": "B", "c": 456}], list, dict),
        (typing.List[MyModel], [{"a": "a", "b": "b", "c": 123}, {"a": "A", "b": "B", "c": 456}], list, dict),
        (tuple[MyModel, ...], ({"a": "a", "b": "b", "c": 123}, {"a": "A", "b": "B", "c": 456}), list, dict),
        (
            typing.Tuple[MyModel, ...],
            ({"a": "a", "b": "b", "c": 123}, {"a": "A", "b": "B", "c": 456}),
            list,
            dict,
        ),
        (dict[str, MyModel], {"val": {"a": "a", "b": "b", "c": 123}}, dict, dict),
        (dict[str, MyModel], {"val": MyModel(a="a", b="b", c=123)}, dict, dict),
        (typing.Dict[str, MyModel], {"val": MyModel(a="a", b="b", c=123)}, dict, dict),
        (MyModelDC, {"a": "a", "b": "b", "c": 123}, dict, str),
        (MyModelDC, MyModelDC(a="a", b="b", c=123), dict, str),
        (MyModelRoot, [{"a": "a", "b": "b", "c": 123}], list, dict),
    ],
)
def test_validate_model_and_json_encode(type_, obj, new_type, member_type):
    obj_new = validate_model(type_, obj)
    obj_new = jsonable_encoder(obj_new)
    assert obj_new is not None
    assert type(obj_new) == new_type

    if isinstance(obj_new, list):
        member = obj_new[0]

    elif isinstance(obj_new, dict):
        member = list(obj_new.values())[0]

    elif member_type is None:
        member = None
        assert type(member) == type(None)

    else:
        assert type(member) == member_type
