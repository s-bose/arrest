from arrest import Service

from .resources import root, tasks, users

API_URL = "http://localhost:8080"

example_service = Service(name="example_service", url=API_URL, resources=[root, tasks, users])
