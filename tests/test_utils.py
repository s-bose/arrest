import pytest
from pydantic import BaseModel

from arrest.utils import deserialize


class MyModel(BaseModel):
    a: str
    b: str
    c: int


def test_deserialize(mocker):
    dct = deserialize(model=MyModel(a="a", b="b", c=123), field="c")
    assert dct == {"c": 123}

    mocker.patch("arrest.utils.PYDANTIC_VERSION", new="1.0", autospec=False)
    dct = deserialize(model=MyModel(a="a", b="b", c=123), field="b")
    assert dct == {"b": "b"}

    dct = deserialize(model=MyModel(a="a", b="b", c=123), field="d")
    assert dct == {}
