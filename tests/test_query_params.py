# import pytest

# from arrest import Resource
# from arrest.http import Methods


# @pytest.mark.parametrize(
#     "method, request_path, expected_handler_route",
#     [
#         (Methods.GET, "/posts?", "/posts"),
#         (Methods.GET, "/posts/?", None),
#         (Methods.GET, "/posts/123?", "/posts/{foo:int}"),
#         (Methods.GET, "/posts/123/?", None),
#         (Methods.GET, "/posts/123/comments?", None),
#         (Methods.GET, "/posts/123/comments/?", None),
#         (
#             Methods.GET,
#             "/posts/123/comments/456?",
#             "/posts/{foo:int}/comments/{bar:int}",
#         ),
#         (
#             Methods.GET,
#             "/posts/123/comments/456/?",
#             None,
#         ),
#     ],
# )
# def test_query_params_kwargs(service, method, request_path, expected_handler_route):
#     service.add_resource(
#         Resource(
#             route="/user",
#             handlers=[
#                 (Methods.GET, "/posts"),
#                 (Methods.GET, "/posts/{foo:int}"),
#                 (Methods.GET, "/posts/{foo:int}/comments/{bar:int}"),
#             ],
#         )
#     )

#     result = service.user.get_matching_handler(
#         method=method, path=request_path, q=123
#     )
#     if result is not None:
#         assert result[0].route == expected_handler_route
#     else:
#         assert result is expected_handler_route
