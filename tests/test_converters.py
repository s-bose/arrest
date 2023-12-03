from contextlib import nullcontext as noraise
from datetime import datetime
from typing import Any

import pytest

from arrest.converters import (
    Converter,
    FloatConverter,
    IntegerConverter,
    StrConverter,
    UUIDConverter,
    add_converter,
    replace_params,
)
from arrest.exceptions import ConversionError

dummy_date = datetime.now()


class NoStr:
    def __str__(self):
        pass


class DatetimeConverter(Converter[datetime]):
    regex = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(.[0-9]+)?"

    def to_str(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%S")


@pytest.mark.parametrize(
    "path, path_params, param_types, returned_path, exception",
    [
        (
            "/profile/{profile_id}",
            {"profile_id": 123},
            {"profile_id": StrConverter()},
            "/profile/123",
            noraise(),
        ),
        (
            "/profile/{profile_id}",
            {"profile_id": 123},
            {"profile_id": IntegerConverter()},
            "/profile/123",
            noraise(),
        ),
        (
            "/profile/{profile_id}",
            {"profile_id": 123},
            {"profile_id": StrConverter()},
            "/profile/123",
            noraise(),
        ),
        (
            "/profile/{profile_id}",
            {"profile_id": 145},
            {"profile_id": FloatConverter()},
            "/profile/145",
            noraise(),
        ),
        (
            "/profile/{profile_id}",
            {"profile_id": 145.56},
            {"profile_id": FloatConverter()},
            "/profile/145.56000000000000227374",
            noraise(),
        ),
        (
            "/profile/{profile_id}",
            {"profile_id": "4d96597f-5d49-4ec0-a400-a4a01efd4b53"},
            {"profile_id": UUIDConverter()},
            "/profile/4d96597f-5d49-4ec0-a400-a4a01efd4b53",
            noraise(),
        ),
        (
            "/profile/{profile_id}",
            {"profile_id": "abc"},
            {"profile_id": Converter()},
            None,
            pytest.raises(NotImplementedError),
        ),
        (
            "/profile/{profile_id}",
            {"profile_id": 123},
            None,
            "/profile/123",
            noraise(),
        ),
        (
            "/profile/{pdate}",
            {"pdate": dummy_date},
            {"pdate": DatetimeConverter()},
            f"/profile/{dummy_date.strftime('%Y-%m-%dT%H:%M:%S')}",
            noraise(),
        ),
    ],
)
def test_converters_convert_and_replace_params(
    path: str,
    path_params: dict,
    param_types: dict,
    returned_path: str,
    exception: Any,
):
    add_converter(DatetimeConverter(), "datetime")

    with exception:
        ret, _ = replace_params(
            path=path, path_params=path_params, param_types=param_types
        )
        assert ret == returned_path


@pytest.mark.parametrize(
    "path, path_params, param_types",
    [
        (
            "/profile/{profile_id}",
            {"profile_id": "notanumber"},
            {"profile_id": IntegerConverter()},
        ),
        (
            "/profile/{profile_id}",
            {"profile_id": "notanumber"},
            {"profile_id": FloatConverter()},
        ),
        (
            "/profile/{profile_id}",
            {"profile_id": "notauuid"},
            {"profile_id": UUIDConverter()},
        ),
        (
            "/profile/{profile_id}",
            {"profile_id": NoStr()},
            {"profile_id": StrConverter()},
        ),
    ],
)
def test_converters_type_error(path, path_params, param_types):
    with pytest.raises(ConversionError):
        replace_params(path=path, path_params=path_params, param_types=param_types)
