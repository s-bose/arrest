from pathlib import Path
from tempfile import TemporaryDirectory

from arrest.openapi.init_template import InitTemplate
from arrest.openapi.resource_template import HandlerSchema, ResourceSchema, ResourceTemplate
from arrest.openapi.service_template import ServiceSchema, ServiceTemplate


def test_init_template():
    str_bytes = InitTemplate(destination_path=Path().resolve()).render()
    assert str_bytes == ""


def test_service_template():
    service = ServiceSchema(
        service_id="user_service_v1",
        name="user_service",
        url="http://www.example.com",
        resources=["Posts", "Comments"],
    )

    with TemporaryDirectory() as tmpdir:
        filepath = tmpdir
        ServiceTemplate(services=[service], destination_path=Path(filepath)).render_and_save()
        with open(f"{tmpdir}/services.py", "r") as file:
            content = file.read()

        assert content == (
            "from arrest import Service\n"
            "from .resources import Comments, Posts\n"
            "\n"
            "user_service_v1 = Service(\n"
            '    name="user_service",\n'
            '    url="http://www.example.com",\n'
            "    resources=[Comments, Posts]\n"
            ")\n"
        )


def test_resource_template():
    resource = ResourceSchema(
        name="user",
        route="/user",
        handlers=[
            HandlerSchema(method="GET", route="/", request="UserRequest", response="UserResponse"),
            HandlerSchema(method="PUT", route="/{userId}", request="UserRequest"),
            HandlerSchema(method="GET", route="/{postsId}"),
        ],
    )

    with TemporaryDirectory() as tmpdir:
        filepath = tmpdir
        ResourceTemplate(
            schema_module="models", resources=[resource], destination_path=Path(filepath)
        ).render_and_save()
        with open(f"{tmpdir}/resources.py", "r") as file:
            content = file.read()

        assert content == (
            "from arrest import Resource\n"
            "from .models import UserRequest, UserResponse\n"
            "\n"
            "user = Resource(\n"
            '    name="user",\n'
            '    route="/user",\n'
            "    handlers=[\n"
            '        ("GET", "/", UserRequest, UserResponse),\n'
            '        ("PUT", "/{userId}", UserRequest, None),\n'
            '        ("GET", "/{postsId}", None, None),\n'
            "    ]\n"
            ")\n"
        )
