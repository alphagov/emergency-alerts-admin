import os

import boto3
from flask import json
from moto import mock_aws

aws_region = os.environ.get("AWS_REGION", "eu-west-2")


@mock_aws
def test_get_status_all_ok(mocker, client_request):
    mocker.patch("app.status_api_client.get_status", return_value={})

    response = client_request.get_response("status.show_status")
    assert response.status_code == 200
    resp_json = json.loads(response.text)
    assert resp_json["status"] == "ok"
    assert resp_json["git_commit"]
    assert resp_json["build_time"]

    cloudwatch = boto3.client("cloudwatch", region_name=aws_region)
    metric = cloudwatch.list_metrics()["Metrics"][0]
    assert metric["MetricName"] == "AppVersion"
    assert metric["Namespace"] == "Emergency Alerts"
    assert {"Name": "Application", "Value": "admin"} in metric["Dimensions"]
