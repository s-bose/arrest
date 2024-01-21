from openapi_pydantic import Operation, RequestBody, Reference

class RequestParser:
    @staticmethod
    def get_request_body(operation: Operation):
        request_body = operation.requestBody
        if isinstance(request_body, RequestBody):
            request_body.
