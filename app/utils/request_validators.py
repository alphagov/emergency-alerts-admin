from functools import wraps

from flask import abort, request


def validate_content_type(content_types: list[str]):
    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            if request.content_type not in content_types:
                abort(400, f"Invalid content type. Must be one of: {', '.join(content_types)}")
            else:
                return func(*args, **kwargs)

        return wrap_func

    return wrap
