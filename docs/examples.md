You can refer to the `example` folder for different use cases.

It comes with a completely functional REST API suite for task management with CRUD operations for `users` and `tasks`.

It uses in-memory dictionaries for data storage, so of course this is just for testing and learning purposes.

It comes with a set of test files which test compatibility with 3 different types.

1. Pydantic BaseModel
2. Python dataclasses
3. No class, rely on dicts and lists

## Packages Used

1. [FastAPI==0.112.2](https://fastapi.tiangolo.com)
2. [Pydantic==2.8.2](https://docs.pydantic.dev/latest/)
3. [Uvicorn==0.30.6](https://www.uvicorn.org/)

## Installation

To run the example FastAPI application, simply go to the example directory at the project root, and run `bash run.sh`, and you shoule be able to access the Swagger docs at [http://localhost:8080/docs]()

Alternatively, you can set up your own virtualenv, and install the `requirements.example.txt` and run `uvicorn app.main:app`.


## Running Tests

Create a virtualenv that contains the dependencies in the example directory, and run `pytest -vvv`.
