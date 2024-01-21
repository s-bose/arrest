from typing import Optional
from openapi_pydantic import Operation, Reference

from arrest.openapi.utils import get_ref_schema


class RequestParser:
    @staticmethod
    def get_request_body(operation: Operation) -> Optional[str]:
        if not (request_body := operation.requestBody):
            return None
        if isinstance(request_body, Reference):
            return get_ref_schema(request_body.ref)
        else:
            if request_body.content and (media := request_body.content.get("application/json", None)):
                return get_ref_schema(media.media_type_schema)
