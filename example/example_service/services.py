from arrest import Service

from .resources import custom, root, tasks, users

example_fastapi_rest_application = Service(
    name="example_fastapi_rest_application", url="/", resources=[custom, root, tasks, users]
)
