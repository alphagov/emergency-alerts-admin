from flask import g


def test_owasp_useful_headers_set(
    client_request,
    mocker,
    mock_get_service_and_organisation_counts,
):
    client_request.logout()
    response = client_request.get_response("main.sign_in")

    assert response.headers["X-Frame-Options"] == "deny"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert response.headers["Content-Security-Policy"] == (
        "default-src 'self' static.example.com;"
        "report-to default;"
        "script-src 'self' static.example.com *.google-analytics.com 'nonce-{content_nonce}' 'unsafe-eval';"
        "style-src 'self' static.example.com 'nonce-{content_nonce}';"
        "connect-src 'self' *.google-analytics.com;"
        "object-src 'self';"
        "font-src 'self' static.example.com data:;"
        "img-src "
        "'self' static.example.com *.tile.openstreetmap.org *.google-analytics.com data:;"
    ).format(content_nonce=g.content_nonce)
    assert response.headers["Link"] == (
        "<https://static.example.com>; rel=dns-prefetch, " "<https://static.example.com>; rel=preconnect"
    )
    assert response.headers["Strict-Transport-Security"] == "max-age=63072000; includeSubdomains; preload"


def test_headers_non_ascii_characters_are_replaced(
    client_request,
    mocker,
    mock_get_service_and_organisation_counts,
):
    client_request.logout()

    response = client_request.get_response("main.sign_in")

    assert response.headers["Content-Security-Policy"] == (
        "default-src 'self' static.example.com;"
        "report-to default;"
        "script-src 'self' static.example.com *.google-analytics.com 'nonce-{content_nonce}' 'unsafe-eval'"
        "'sha256-YX4iJw93x5SU0ple+RI+95HNdNBZSA60gR8a5v7HfOA=';"
        "style-src 'self' static.example.com 'nonce-{content_nonce}';"
        "connect-src 'self' *.google-analytics.com;"
        "object-src 'self';"
        "font-src 'self' static.example.com data:;"
        "img-src "
        "'self' static.example.com *.tile.openstreetmap.org *.google-analytics.com data:;"
    ).format(content_nonce=g.content_nonce)
