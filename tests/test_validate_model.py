import pytest
from typing import Optional, TypeAlias, List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel
from arrest.utils import validate_model
from arrest._config import PYDANTIC_V2


class MyModel(BaseModel):
    username: str
    password: str
    country: Optional[str]
    created_at: Optional[datetime] = datetime.utcnow()


ListType1: TypeAlias = list[MyModel]
ListType2: TypeAlias = List[MyModel]
DictType1: TypeAlias = dict[str, MyModel]
DictType2: TypeAlias = Dict[str, MyModel]


def test_validate_model():
    instance = MyModel(username="abc", password="123", country="IND")

    assert (
        validate_model(MyModel, {"username": "abc", "password": "123", "country": "IND"})
        == validate_model(MyModel, instance)
        == instance
    )


@pytest.mark.parametrize("type_", (ListType1, ListType2))
def test_validate_model_list(type_):
    instances = [
        MyModel(username="A", password="1", country="US"),
        MyModel(username="B", password="2", country="AU"),
        MyModel(username="C", password="3", country="CN"),
    ]

    if PYDANTIC_V2:
        instances_list_of_dict = [instance.model_dump() for instance in instances]
    else:
        instances_list_of_dict = [instance.dict() for instance in instances]

    assert validate_model(type_, instances) == validate_model(type_, instances_list_of_dict)


@pytest.mark.parametrize("type_", (DictType1, DictType2))
def test_validate_model_dict(type_):
    instances = {
        "A": MyModel(username="A", password="1", country="US"),
        "B": MyModel(username="B", password="2", country="AU"),
        "C": MyModel(username="C", password="3", country="CN"),
    }

    if PYDANTIC_V2:
        instances_dict = {k: instance.model_dump() for k, instance in instances.items()}
    else:
        instances_dict = {k: instance.dict() for k, instance in instances.items()}

    assert validate_model(type_, instances) == validate_model(type_, instances_dict)


def test_validate_model_optional():
    instance = MyModel(username="abc", password="123", country="IND")

    if PYDANTIC_V2:
        instance_dict = instance.model_dump()
    else:
        instance_dict = instance.dict()

    assert validate_model(Optional[MyModel], instance) == validate_model(Optional[MyModel], instance_dict)

    assert validate_model(Optional[MyModel], None) is None
