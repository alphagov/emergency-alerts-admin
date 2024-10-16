from app.utils.pagination import generate_next_dict


def test_generate_previous_next_dict_adds_other_url_args(client_request):
    result = generate_next_dict("main.view_notifications", "foo", 2, {"message_type": "blah"})
    assert "notifications/blah" in result["url"]
