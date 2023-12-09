from pydantic import BaseModel

from arrest.utils import extract_model_field


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
