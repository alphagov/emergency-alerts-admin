import os

from flask import current_app, jsonify, request

from app import status_api_client, version
from app.status import status


@status.route("/_admin_status", methods=["GET"])
def show_status():
    if request.args.get("elb", None) or request.args.get("simple", None):
        return jsonify(status="ok"), 200
    else:
        try:
            api_status = status_api_client.get_status()
        except Exception as e:
            current_app.logger.exception("API failed to respond")
            return jsonify(status="error", message=str(e.message)), 500
        return (
            jsonify(
                status="ok",
                api=api_status,
                git_commit=version.__git_commit__,
                build_time=version.__time__,
                app_version=get_app_version(),
            ),
            200,
        )


def get_app_version():
    if os.getenv("APP_VERSION") is not None:
        return os.getenv("APP_VERSION")
    else:
        return "0.0.0"
