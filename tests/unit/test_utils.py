import enum
import typing
from dataclasses import dataclass
from datetime import datetime

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
    retry,
    validate_model,
)


class MyModel(BaseModel):
    a: str
    b: str
    c: int


ListType1: typing.TypeAlias = list[MyModel]
ListType2: typing.TypeAlias = typing.List[MyModel]
DictType1: typing.TypeAlias = dict[str, MyModel]
DictType2: typing.TypeAlias = typing.Dict[str, MyModel]


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
        pytest.param(str, "abc", str, None),
        (int, 123, int, None),
        (float, 123.4, float, None),
        (MyEnum, "field", MyEnum, None),
        (MyEnum, MyEnum.field, MyEnum, None),
        (list[int], [1, 2, 3], list, int),
        (list[MyEnum], ["field"], list, MyEnum),
        (MyModel, {"a": "a", "b": "b", "c": 123}, MyModel, None),
        (MyModel, MyModel(a="a", b="b", c=123), MyModel, None),
        (list[MyModel], [{"a": "a", "b": "b", "c": 123}, {"a": "A", "b": "B", "c": 456}], list, MyModel),
        (
            typing.List[MyModel],
            [{"a": "a", "b": "b", "c": 123}, {"a": "A", "b": "B", "c": 456}],
            list,
            MyModel,
        ),
        (
            tuple[MyModel, ...],
            ({"a": "a", "b": "b", "c": 123}, {"a": "A", "b": "B", "c": 456}),
            tuple,
            MyModel,
        ),
        (
            typing.Tuple[MyModel, ...],
            ({"a": "a", "b": "b", "c": 123}, {"a": "A", "b": "B", "c": 456}),
            tuple,
            MyModel,
        ),
        (dict[str, MyModel], {"val": {"a": "a", "b": "b", "c": 123}}, dict, MyModel),
        (dict[str, MyModel], {"val": MyModel(a="a", b="b", c=123)}, dict, MyModel),
        (typing.Dict[str, MyModel], {"val": MyModel(a="a", b="b", c=123)}, dict, MyModel),
        (MyModelDC, {"a": "a", "b": "b", "c": 123}, MyModelDC, None),
        (MyModelDC, MyModelDC(a="a", b="b", c=123), MyModelDC, None),
        (MyModelRoot, [{"a": "a", "b": "b", "c": 123}], MyModelRoot, None),
        (datetime, datetime.now(), datetime, None),
        (datetime, "2024-04-24 02:25:14.954853", datetime, None),
        (typing.Optional[MyModel], MyModel(a="a", b="b", c=123), MyModel, None),
        (typing.Optional[MyModel], {"a": "a", "b": "b", "c": 123}, MyModel, None),
        (typing.Optional[MyModel], None, type(None), None),
    ],
)
def test_validate_model(type_, obj, new_type, member_type):
    obj_new = validate_model(type_, obj)

    assert isinstance(obj_new, new_type)

    member = None
    if isinstance(obj_new, (list, tuple)):
        member = obj_new[0]

    elif isinstance(obj_new, dict):
        member = list(obj_new.values())[0]

    elif member_type is None:
        pass

    else:
        assert isinstance(member, member_type)


@pytest.mark.parametrize(
    argnames="obj, obj_serialized",
    argvalues=[
        ("abc", "abc"),
        (123, 123),
        (123.4, 123.4),
        (MyEnum.field, "field"),
        ([1, 2, 3], [1, 2, 3]),
        ([MyEnum.field], ["field"]),
        (MyModel(a="a", b="b", c=123), {"a": "a", "b": "b", "c": 123}),
        (
            [MyModel(a="a", b="b", c=123), MyModel(a="A", b="B", c=456)],
            [{"a": "a", "b": "b", "c": 123}, {"a": "A", "b": "B", "c": 456}],
        ),
        (
            (MyModel(a="a", b="b", c=123), MyModel(a="A", b="B", c=456)),
            [{"a": "a", "b": "b", "c": 123}, {"a": "A", "b": "B", "c": 456}],
        ),
        ({"val": MyModel(a="a", b="b", c=123)}, {"val": {"a": "a", "b": "b", "c": 123}}),
        (MyModelDC(a="a", b="b", c=123), {"a": "a", "b": "b", "c": 123}),
        (
            [MyModelDC(a="a", b="b", c=123), MyModelDC(a="A", b="B", c=456)],
            [{"a": "a", "b": "b", "c": 123}, {"a": "A", "b": "B", "c": 456}],
        ),
        (
            (MyModelDC(a="a", b="b", c=123), MyModelDC(a="A", b="B", c=456)),
            [{"a": "a", "b": "b", "c": 123}, {"a": "A", "b": "B", "c": 456}],
        ),
        ({"val": MyModelDC(a="a", b="b", c=123)}, {"val": {"a": "a", "b": "b", "c": 123}}),
        (datetime(year=2023, month=1, day=1), "2023-01-01T00:00:00"),
    ],
)
def test_jsonable_encoder(obj, obj_serialized):
    assert jsonable_encoder(obj) == obj_serialized


def test_jsonable_encoder_rootmodel():
    if PYDANTIC_V2:
        obj = MyModelRoot(root=[MyModel(a="a", b="b", c=123)])
    else:
        obj = MyModelRoot(__root__=[MyModel(a="a", b="b", c=123)])

    obj_serialized = [{"a": "a", "b": "b", "c": 123}]

    assert jsonable_encoder(obj) == obj_serialized


def test_jsonable_encoder_standard_object():
    class PlainClass:
        def __init__(self, first: str, second: int) -> None:
            self.first = first
            self.second = second

    obj = PlainClass(first="first", second=123)
    obj_serialized = {"first": "first", "second": 123}

    assert jsonable_encoder(obj) == obj_serialized


def test_jsonable_encoder_object_with_no___dict__():
    class PlainClass:
        __slots__ = ()

    obj = PlainClass()
    with pytest.raises(ValueError):
        jsonable_encoder(obj)


@pytest.mark.asyncio
async def test_retry_async(mocker):
    class Foo:
        @retry(n_retries=3, exceptions=(ValueError))
        async def fn_async(self):
            print("baz")
            raise ValueError()

        @retry(n_retries=2, exceptions=(Exception))
        def fn_sync():
            print("baz sync")
            raise Exception()

    spy = mocker.spy(Foo, "fn_async")
    spy_sync = mocker.spy(Foo, "fn_sync")

    foo = Foo()

    with pytest.raises(ValueError):
        await foo.fn_async()
        assert spy.call_count == 3

    with pytest.raises(Exception):
        foo.fn_sync()
        assert spy_sync.call_count == 2
