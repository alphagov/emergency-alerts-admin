from functools import wraps

from flask import abort, g, make_response
from werkzeug.routing import RequestRedirect

BROADCAST_TYPE = "broadcast"


def service_has_permission(permission):
    from app import current_service

    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            if not current_service or not current_service.has_permission(permission):
                abort(403)
            return func(*args, **kwargs)

        return wrap_func

    return wrap


def service_belongs_to_org_type(org_type):
    from app import current_service

    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            if not current_service or not current_service.organisation_type == org_type:
                abort(403)
            return func(*args, **kwargs)

        return wrap_func

    return wrap


class PermanentRedirect(RequestRedirect):
    """
    In Werkzeug 0.15.0 the status code for RequestRedirect changed from 301 to 308.
    308 status codes are not supported when Internet Explorer is used with Windows 7
    and Windows 8.1, so this class keeps the original status code of 301.
    """

    code = 301


def hide_from_search_engines(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.hide_from_search_engines = True
        response = make_response(f(*args, **kwargs))
        response.headers["X-Robots-Tag"] = "noindex"
        return response

    return decorated_function


# Function to merge two dict or lists with a JSON-like structure into one.
# JSON-like means they can contain all types JSON can: all the main primitives
# plus nested lists or dictionaries.
# Merge is additive. New values overwrite old and collections are added to.
def merge_jsonlike(source, destination):
    def merge_items(source_item, destination_item):
        if isinstance(source_item, dict) and isinstance(destination_item, dict):
            merge_dicts(source_item, destination_item)
        elif isinstance(source_item, list) and isinstance(destination_item, list):
            merge_lists(source_item, destination_item)
        else:  # primitive value
            return False
        return True

    def merge_lists(source, destination):
        last_src_idx = len(source) - 1
        for idx, item in enumerate(destination):
            if idx <= last_src_idx:
                # assign destination value if can't be merged into source
                if merge_items(source[idx], destination[idx]) is False:
                    source[idx] = destination[idx]
            else:
                source.append(item)

    def merge_dicts(source, destination):
        for key, value in destination.items():
            if key in source:
                # assign destination value if can't be merged into source
                if merge_items(source[key], value) is False:
                    source[key] = value
            else:
                source[key] = value

    merge_items(source, destination)
