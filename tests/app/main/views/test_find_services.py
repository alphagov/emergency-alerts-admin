# Most relevant tests for this are run in test_platform_admin.py
def test_find_services_by_name_validates_against_empty_search_submission(client_request, platform_admin_user, mocker):
    client_request.login(platform_admin_user)
    document = client_request.post("main.find_services_by_name", _data={"search": ""}, _expected_status=200)

    expected_message = "Error: You need to enter full or partial name to search by."
    assert document.select_one(".govuk-error-message").text.strip() == expected_message
