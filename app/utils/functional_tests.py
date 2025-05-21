from flask import current_app, request


def is_request_from_functional_tests():
    """
    See if the current request context has come from a known functional test IP
    (if configured for the environment)
    """

    for ip in current_app.config["FUNCTIONAL_TEST_IPS"]:
        if request.remote_addr == ip:
            return True

    return False
