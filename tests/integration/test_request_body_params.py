import json
import typing
from dataclasses import dataclass
from datetime import datetime

import httpx
import pytest
from pydantic import BaseModel, RootModel
from pydantic import ValidationError as PydanticValidationError
from pydantic_xml import BaseXmlModel, attr, element
from respx.patterns import M

from arrest.http import Methods
from arrest.params import Body, File, Form
from arrest.resource import Resource
from arrest.types import UploadFile


class UserRequest(BaseModel):
    id: int
    name: str = Body(...)  # type: ignore
    email: str
    dob: typing.Optional[datetime] = None


@dataclass
class UserRequestDC:
    id: int
    name: str
    email: str
    dob: typing.Optional[datetime] = None


class UserRequestRoot(RootModel):
    root: list[UserRequest]


@pytest.mark.parametrize(
    "request_body, request_type, parsed_body, exception",
    [
        # pydantic models
        (
            {"id": 0, "name": "username", "email": "user@email.com"},
            UserRequest,
            {"id": 0, "name": "username", "email": "user@email.com", "dob": None},
            None,
        ),
        (
            UserRequest(id=123, name="username", email="user@email.com"),
            UserRequest,
            {"id": 123, "name": "username", "email": "user@email.com", "dob": None},
            None,
        ),
        (
            {"id": 0, "name": "username", "foo": "bar"},
            UserRequest,
            None,
            PydanticValidationError,
        ),
        # dataclasses
        (
            {"id": 0, "name": "username", "email": "user@email.com"},
            UserRequestDC,
            {"id": 0, "name": "username", "email": "user@email.com", "dob": None},
            None,
        ),
        (
            UserRequestDC(id=123, name="username", email="user@email.com"),
            UserRequestDC,
            {"id": 123, "name": "username", "email": "user@email.com", "dob": None},
            None,
        ),
        (
            {"id": 0, "name": "username", "foo": "bar"},
            UserRequestDC,
            None,
            PydanticValidationError,
        ),
        # list types
        (
            [{"id": 0, "name": "username", "email": "user@email.com"}],
            list[UserRequest],
            [{"id": 0, "name": "username", "email": "user@email.com", "dob": None}],
            None,
        ),
        (
            [
                {"id": 0, "name": "username1", "email": "user1@email.com"},
                {"id": 1, "name": "username2", "email": "user2@email.com"},
            ],
            list[UserRequest],
            [
                {"id": 0, "name": "username1", "email": "user1@email.com", "dob": None},
                {"id": 1, "name": "username2", "email": "user2@email.com", "dob": None},
            ],
            None,
        ),
        (
            [UserRequest(id=123, name="username", email="user@email.com")],
            list[UserRequest],
            [{"id": 123, "name": "username", "email": "user@email.com", "dob": None}],
            None,
        ),
        (
            [{"id": 0, "name": "username", "foo": "bar"}],
            list[UserRequest],
            None,
            PydanticValidationError,
        ),
        (
            [{"id": 0, "name": "username", "email": "user@email.com"}],
            list[UserRequestDC],
            [{"id": 0, "name": "username", "email": "user@email.com", "dob": None}],
            None,
        ),
        (
            [UserRequestDC(id=123, name="username", email="user@email.com")],
            list[UserRequestDC],
            [{"id": 123, "name": "username", "email": "user@email.com", "dob": None}],
            None,
        ),
        (
            [{"id": 0, "name": "username", "foo": "bar"}],
            list[UserRequestDC],
            None,
            PydanticValidationError,
        ),
        # pydantic root models
        (
            [{"id": 0, "name": "username", "email": "user@email.com"}],
            UserRequestRoot,
            [{"id": 0, "name": "username", "email": "user@email.com", "dob": None}],
            None,
        ),
        (
            UserRequestRoot(
                root=[{"id": 0, "name": "username", "email": "user@email.com"}]  # type: ignore
            ),
            UserRequestRoot,
            [{"id": 0, "name": "username", "email": "user@email.com", "dob": None}],
            None,
        ),
    ],
)
@pytest.mark.asyncio
async def test_body_request_json(
    service,
    mock_httpx,
    request_body: BaseModel | list | dict,
    request_type: typing.Any,
    parsed_body: dict | list | None,
    exception: Exception | None,
):
    patterns = [
        M(url__regex="/user/*", method__in=["POST"]),
    ]

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (
                    Methods.POST,
                    "/profile",
                    request_type,
                ),
            ],
        )
    )

    if exception:
        with pytest.raises(exception):
            await service.user.post("/profile", request=request_body)
    else:
        mock_httpx.route(*patterns, name="http_request").mock(
            return_value=httpx.Response(200, json={"status": "OK"})
        )
        await service.user.post("/profile", request=request_body)

        request: httpx.Request = mock_httpx["http_request"].calls[0].request
        request_body = json.loads(request.content)
        assert parsed_body == request_body


class FormOnlyRequest(BaseModel):
    name: str = Form(...)
    email: str = Form(...)


class FileOnlyRequest(BaseModel):
    name: str = Form(...)
    avatar: typing.Any = File(...)


class MixedBodyFormRequest(BaseModel):
    name: str = Body(...)
    email: str = Form(...)


# Form-encoded (urlencoded) tests


@pytest.mark.parametrize(
    "form_data, expected_fields",
    [
        (
            {"name": "alice", "email": "alice@example.com"},
            {"name": "alice", "email": "alice@example.com"},
        ),
        (
            FormOnlyRequest(name="bob", email="bob@example.com"),
            {"name": "bob", "email": "bob@example.com"},
        ),
    ],
)
@pytest.mark.asyncio
async def test_body_request_form_urlencoded(
    service,
    mock_httpx,
    form_data,
    expected_fields,
):
    patterns = [M(url__regex="/user/*", method__in=["POST"])]

    service.add_resource(
        Resource(
            route="/user",
            handlers=[(Methods.POST, "/form", FormOnlyRequest)],
        )
    )

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )
    await service.user.post("/form", request=form_data)

    req: httpx.Request = mock_httpx["http_request"].calls[0].request
    assert req.headers["content-type"] == "application/x-www-form-urlencoded"
    # httpx sends urlencoded body; parse it back for assertions
    from urllib.parse import parse_qs

    parsed = parse_qs(req.content.decode())
    for key, val in expected_fields.items():
        assert parsed[key] == [val]


# Multipart / file tests


@pytest.mark.parametrize(
    "file_data, form_name",
    [
        (b"hello world", "alice"),
    ],
)
@pytest.mark.asyncio
async def test_body_request_form_multipart(
    service,
    mock_httpx,
    file_data,
    form_name,
):
    patterns = [M(url__regex="/user/*", method__in=["POST"])]

    service.add_resource(
        Resource(
            route="/user",
            handlers=[(Methods.POST, "/upload", FileOnlyRequest)],
        )
    )

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )
    await service.user.post(
        "/upload",
        request=FileOnlyRequest(name=form_name, avatar=file_data),
    )

    req: httpx.Request = mock_httpx["http_request"].calls[0].request
    ct = req.headers["content-type"]
    assert ct.startswith("multipart/form-data"), f"expected multipart, got {ct}"
    # body should contain the form field and file content
    body = req.content.decode()
    assert form_name in body
    assert "hello world" in body


@pytest.mark.asyncio
async def test_body_request_form_file_uploadfile(service, mock_httpx):
    """Cover extract_file_params UploadFile branch."""
    import io

    patterns = [M(url__regex="/user/*", method__in=["POST"])]

    service.add_resource(
        Resource(
            route="/user",
            handlers=[(Methods.POST, "/upload", FileOnlyRequest)],
        )
    )

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )

    file_obj = io.BytesIO(b"file content bytes")
    upload = UploadFile(filename="test.txt", content_type="text/plain", file=file_obj)

    await service.user.post(
        "/upload",
        request=FileOnlyRequest(name="carol", avatar=upload),
    )

    req: httpx.Request = mock_httpx["http_request"].calls[0].request
    ct = req.headers["content-type"]
    assert ct.startswith("multipart/form-data")
    body = req.content.decode()
    assert "carol" in body
    assert "file content bytes" in body
    assert "test.txt" in body


# Conflict detection


@pytest.mark.asyncio
async def test_body_request_mixed_body_form_raises(service, mock_httpx):
    service.add_resource(
        Resource(
            route="/user",
            handlers=[(Methods.POST, "/mixed", MixedBodyFormRequest)],
        )
    )

    with pytest.raises(ValueError, match="Cannot mix JSON body fields"):
        await service.user.post(
            "/mixed",
            request={"name": "test", "email": "test@test.com"},
        )


# extract_file_params edge cases


class FileStringRequest(BaseModel):
    name: str = Form(...)
    doc: str = File(...)


def test_extract_file_params_string_and_errors():
    """Cover extract_file_params str branch and error branches."""
    from arrest.utils import extract_file_params

    # string → encode to bytes
    model = FileStringRequest(name="x", doc="hello")
    result = extract_file_params(model, "doc")
    assert result == {"doc": b"hello"}

    # non-File field → ValueError
    with pytest.raises(ValueError, match="is not a file field"):
        extract_file_params(model, "name")

    # UploadFile with no file → ValueError
    upload = UploadFile(filename="x.txt", file=None)
    file_model = FileOnlyRequest(name="x", avatar=upload)
    with pytest.raises(ValueError, match="has no file provided"):
        extract_file_params(file_model, "avatar")


# Handler-level content-type override


@pytest.mark.parametrize(
    "handler_headers, call_headers, expected_ct",
    [
        pytest.param(
            {"Content-Type": "multipart/form-data"},
            None,
            "multipart/form-data",
            id="handler overrides annotation-derived",
        ),
        pytest.param(
            {"Content-Type": "multipart/form-data"},
            {"Content-Type": "application/x-custom"},
            "application/x-custom",
            id="runtime overrides handler",
        ),
        pytest.param(
            None,
            None,
            "application/x-www-form-urlencoded",
            id="no override: annotation-derived wins",
        ),
    ],
)
@pytest.mark.asyncio
async def test_body_request_handler_level_content_type_override(
    service, mock_httpx, handler_headers, call_headers, expected_ct
):
    """Handler-level Content-Type (via H(headers={...})) takes effect
    for form-data requests, and runtime headers still win."""
    from arrest.handler import H

    patterns = [M(url__regex="/user/*", method__in=["POST"])]

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                H(
                    Methods.POST,
                    "/form",
                    FormOnlyRequest,
                    headers=handler_headers,
                )
            ],
        )
    )

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )
    await service.user.post(
        "/form",
        request={"name": "frank", "email": "frank@example.com"},
        headers=call_headers,
    )

    req: httpx.Request = mock_httpx["http_request"].calls[0].request
    assert req.headers["content-type"] == expected_ct


# UploadFile tests


def test_upload_file_read_without_file_raises():
    uf = UploadFile(filename="test.txt")
    with pytest.raises(ValueError, match="No file provided"):
        uf.read()


def test_upload_file_pydantic_validation_from_file_like():
    """UploadFile schema validates a file-like object with .read() and .name."""
    from pydantic import TypeAdapter

    adapter = TypeAdapter(UploadFile)

    class FakeFile:
        filename = "data.csv"

        def read(self, size=-1):
            return b"col1,col2"

    result = adapter.validate_python(FakeFile())
    assert isinstance(result, UploadFile)
    assert result.filename == "data.csv"
    assert result.read() == b"col1,col2"


def test_upload_file_pydantic_validation_passes_through_existing():
    """UploadFile schema passes through an existing UploadFile instance."""
    from pydantic import TypeAdapter

    adapter = TypeAdapter(UploadFile)
    existing = UploadFile(filename="x.csv", file=None)
    result = adapter.validate_python(existing)
    assert result is existing


def test_upload_file_pydantic_validation_rejects_non_file():
    """UploadFile schema rejects values without a .read() method."""
    from pydantic import TypeAdapter

    adapter = TypeAdapter(UploadFile)
    with pytest.raises(ValueError, match="file-like object"):
        adapter.validate_python("not a file")


@pytest.mark.asyncio
async def test_body_request_resource_level_content_type_override(service, mock_httpx):
    """When Content-Type is set at resource config, it overrides annotation-derived."""
    from arrest._config import ArrestConfig

    patterns = [M(url__regex="/user/*", method__in=["POST"])]

    service.add_resource(
        Resource(
            route="/user",
            handlers=[(Methods.POST, "/form", FormOnlyRequest)],
            config=ArrestConfig(headers={"Content-Type": "multipart/form-data"}),
        )
    )

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )
    await service.user.post(
        "/form", request={"name": "dave", "email": "dave@example.com"}
    )

    req: httpx.Request = mock_httpx["http_request"].calls[0].request
    assert req.headers["content-type"] == "multipart/form-data"


# Runtime-level content-type override


@pytest.mark.asyncio
async def test_body_request_runtime_level_content_type_override(service, mock_httpx):
    """When Content-Type is passed at call time via headers=,
    it overrides the annotation-derived content-type."""
    patterns = [M(url__regex="/user/*", method__in=["POST"])]

    service.add_resource(
        Resource(
            route="/user",
            handlers=[(Methods.POST, "/form", FormOnlyRequest)],
        )
    )

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "OK"})
    )
    await service.user.post(
        "/form",
        request={"name": "eve", "email": "eve@example.com"},
        headers={"Content-Type": "multipart/form-data"},
    )

    req: httpx.Request = mock_httpx["http_request"].calls[0].request
    assert req.headers["content-type"] == "multipart/form-data"


# XML request / response tests


class XmlUserRequest(BaseXmlModel, tag="user"):
    name: str = element()
    email: str = element()


class XmlUserResponse(BaseXmlModel, tag="user"):
    id: int = attr()
    name: str = element()
    email: str = element()


@pytest.mark.asyncio
async def test_xml_request_body(service, mock_httpx):
    """BaseXmlModel request is serialized to XML with correct content-type."""
    patterns = [M(url__regex="/user/*", method__in=["POST"])]

    service.add_resource(
        Resource(
            route="/user",
            handlers=[(Methods.POST, "/xml", XmlUserRequest)],
        )
    )

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(
            200,
            content=b"<user id='1'><name>Alice</name><email>alice@test.com</email></user>",
        )
    )

    resp = await service.user.post(
        "/xml",
        request=XmlUserRequest(name="Alice", email="alice@test.com"),
    )

    req: httpx.Request = mock_httpx["http_request"].calls[0].request
    assert req.headers["content-type"] == "application/xml"
    assert "<user>" in req.content.decode()
    assert "<name>Alice</name>" in req.content.decode()
    assert resp.is_success


@pytest.mark.asyncio
async def test_xml_response_parsing(service, mock_httpx):
    """BaseXmlModel response_type parses XML response into model instance."""
    patterns = [M(url__regex="/user/*", method__in=["GET"])]

    service.add_resource(
        Resource(
            route="/user",
            handlers=[
                (Methods.GET, "/{user_id}", None, XmlUserResponse),
            ],
        )
    )

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(
            200,
            content=b"<user id='42'><name>Bob</name><email>bob@test.com</email></user>",
        )
    )

    resp = await service.user.get("/42")
    assert resp.is_success
    assert isinstance(resp.data, XmlUserResponse)
    assert resp.data.id == 42
    assert resp.data.name == "Bob"
    assert resp.data.email == "bob@test.com"


@pytest.mark.asyncio
async def test_xml_request_no_response_type(service, mock_httpx):
    """BaseXmlModel request with no response type still works."""
    patterns = [M(url__regex="/user/*", method__in=["POST"])]

    service.add_resource(
        Resource(
            route="/user",
            handlers=[(Methods.POST, "/xml", XmlUserRequest)],
        )
    )

    mock_httpx.route(*patterns, name="http_request").mock(
        return_value=httpx.Response(200, json={"status": "created"})
    )

    resp = await service.user.post(
        "/xml",
        request=XmlUserRequest(name="Carol", email="carol@test.com"),
    )

    req: httpx.Request = mock_httpx["http_request"].calls[0].request
    assert req.headers["content-type"] == "application/xml"
    assert resp.data == {"status": "created"}
