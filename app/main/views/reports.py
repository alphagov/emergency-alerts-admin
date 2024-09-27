import json

from app import csrf, reports_api_client, request
from app.main import main
from app.utils.request_validators import validate_content_type


@csrf.exempt
@main.route("/reports", methods=["POST"])
@validate_content_type(content_types=["application/reports+json"])
def reports():
    expected_keys = {"type", "url", "user_agent", "body"}
    if all(key in request.get_json() for key in expected_keys):
        return reports_api_client.post_report(
            data=json.dumps(dict(sorted({key: request.get_json()[key] for key in expected_keys}.items())))
        )
    else:
        return {
            "error": "The request did not conform to the schema for reports. "
            "The request must include a 'type', the 'url', the 'user_agent', and the report 'body'."
        }, 400
