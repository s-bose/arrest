from typing import IO, Any, Callable

from pydantic_core import core_schema

ExceptionHandler = Callable[[Exception], Any]
ExceptionHandlers = dict[type[Exception], ExceptionHandler]


class UploadFile:
    def __init__(
        self,
        filename: str | None = None,
        content_type: str = "application/octet-stream",
        file: IO[bytes] | None = None,
    ):
        self.filename = filename
        self.content_type = content_type
        self.file = file

    def read(self, size: int = -1) -> bytes:
        if self.file is None:
            raise ValueError("No file provided")
        return self.file.read(size)

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        def _validate(v: Any) -> "UploadFile":
            if isinstance(v, cls):
                return v
            if hasattr(v, "read") and callable(v.read):
                filename = getattr(v, "filename", "") or getattr(v, "name", "")
                content_type = getattr(v, "content_type", "application/octet-stream")
                return cls(filename=filename, content_type=content_type, file=v)
            raise ValueError("Value must be a file-like object with a read() method")

        return core_schema.no_info_plain_validator_function(_validate)
