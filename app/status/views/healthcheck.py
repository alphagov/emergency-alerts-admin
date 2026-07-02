import os

import boto3
from flask import current_app, jsonify, request

from app import status_api_client, version
from app.status import status

aws_region = os.environ.get("AWS_REGION", "eu-west-2")


@status.route("/_admin_status", methods=["GET"])
def show_status():
    post_version_to_cloudwatch()

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
                git_commit=version.git_commit,
                build_time=version.time,
                app_version=version.app_version,
            ),
            200,
        )


def post_version_to_cloudwatch():
    try:
        boto3.client("cloudwatch", region_name=aws_region).put_metric_data(
            MetricData=[
                {
                    "MetricName": "AppVersion",
                    "Dimensions": [
                        {
                            "Name": "Application",
                            "Value": "admin",
                        },
                        {
                            "Name": "Version",
                            "Value": version.app_version,
                        },
                    ],
                    "Unit": "Count",
                    "Value": 1,
                }
            ],
            Namespace="Emergency Alerts",
        )
    except Exception:
        current_app.logger.exception(
            "Couldn't post app version to CloudWatch. App version: %s",
        )
