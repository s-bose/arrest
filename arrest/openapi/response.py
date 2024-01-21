from typing import Optional

import httpx
from openapi_pydantic import Operation, Reference

from arrest.logging import logger
from arrest.openapi.utils import get_ref_schema


class ResponseParser:
    @staticmethod
    def get_response_model(operation: Operation) -> Optional[str]:
        if not operation.responses or not (
            success_response := operation.responses.get(str(httpx.codes.OK), None)
        ):
            logger.debug("no success (200) response defined")
            return None

        if isinstance(success_response, Reference):
            return get_ref_schema(success_response)
        else:
            if success_response.content and (media := success_response.content.get("application/json", None)):
                return get_ref_schema(media.media_type_schema)
