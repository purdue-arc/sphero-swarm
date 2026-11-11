"""Test client that looks like the dashboard talking to a coordinator on localhost:8000.

The coordinator refuses requests whose Host is not the local dashboard, and refuses
non-GET requests that are not application/json. This client sends the Host header
the dashboard sends, and gives unsafe requests a JSON body of {} when the test does
not pass one, the same way dashboard.html's api() helper does.
"""
from flask.testing import FlaskClient

LOCAL_BASE_URL = "http://localhost:8000"
UNSAFE_METHODS = ("POST", "PUT", "PATCH", "DELETE")


class LocalClient(FlaskClient):
    def open(self, *args, **kwargs):
        kwargs.setdefault("base_url", LOCAL_BASE_URL)
        if kwargs.get("method") in UNSAFE_METHODS and "json" not in kwargs and "data" not in kwargs:
            kwargs["json"] = {}
        return super().open(*args, **kwargs)
