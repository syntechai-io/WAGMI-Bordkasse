"""Regression tests for the first-visit login CSRF bootstrap."""

import re

from starlette.testclient import TestClient

from main import app


def test_first_login_page_renders_the_token_from_its_cookie():
    client = TestClient(app)
    response = client.get("/login")

    assert response.status_code == 200
    csrf_cookie = client.cookies.get("csrftoken")
    assert csrf_cookie

    match = re.search(
        r'<form method="post" action="/login"[\s\S]*?'
        r'<input type="hidden" name="csrftoken" value="([^"]+)"',
        response.text,
    )
    assert match
    assert match.group(1) == csrf_cookie


def test_login_post_with_rendered_token_reaches_authentication():
    client = TestClient(app)
    response = client.get("/login")
    csrf_cookie = client.cookies.get("csrftoken")

    post_response = client.post(
        "/login",
        data={
            "username": "csrf-regression-invalid-user",
            "password": "invalid-password",
            "trip_id": "",
            "csrftoken": csrf_cookie,
        },
        follow_redirects=False,
    )

    assert post_response.status_code == 303
    assert post_response.headers["location"] == "/login"