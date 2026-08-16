"""CSRF middleware helpers.

The third-party middleware creates the CSRF cookie while sending the response.
That means a first-time GET would otherwise render templates with a missing
token, even though the browser receives a cookie immediately afterwards.
"""

from http.cookies import SimpleCookie
from typing import Any, Callable, Coroutine

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import Message, Receive, Scope, Send

from fastapi_csrf_jinja.middleware import FastAPICSRFJinjaMiddleware


class BootstrapFastAPICSRFJinjaMiddleware(FastAPICSRFJinjaMiddleware):
    """Render the first safe response with the CSRF token it sets."""

    _SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
    _SEED_STATE_KEY = "crewlog_csrf_seed"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            request = Request(scope, receive)
            if request.method in self._SAFE_METHODS and not request.cookies.get(
                self.cookie_name
            ):
                token = self._generate_csrf_token()
                scope[self._SEED_STATE_KEY] = token
                self._append_cookie_to_scope(scope, token)

        await super().__call__(scope, receive, send)

    def _append_cookie_to_scope(self, scope: Scope, token: str) -> None:
        """Make the generated token visible to the request/template processor."""
        headers = list(scope.get("headers", []))
        token_cookie = f"{self.cookie_name}={token}".encode("latin-1")

        for index, (name, value) in enumerate(headers):
            if name.lower() == b"cookie":
                separator = b"; " if value else b""
                headers[index] = (name, value + separator + token_cookie)
                scope["headers"] = headers
                return

        headers.append((b"cookie", token_cookie))
        scope["headers"] = headers

    async def send(
        self,
        message: Message,
        send: Send,
        scope: Scope,
    ) -> None:
        """Set the same token that was exposed to the first safe response."""
        token = scope.get(self._SEED_STATE_KEY)
        if token and message["type"] == "http.response.start":
            message.setdefault("headers", [])
            headers = MutableHeaders(scope=message)
            cookie = SimpleCookie()
            cookie[self.cookie_name] = token
            cookie[self.cookie_name]["path"] = self.cookie_path
            cookie[self.cookie_name]["secure"] = self.cookie_secure
            cookie[self.cookie_name]["httponly"] = False
            cookie[self.cookie_name]["samesite"] = self.cookie_samesite
            if self.cookie_domain is not None:
                cookie[self.cookie_name]["domain"] = self.cookie_domain
            headers.append("set-cookie", cookie.output(header="").strip())

        await send(message)