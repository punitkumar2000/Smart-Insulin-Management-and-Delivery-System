"""Small HTTP client used by the Streamlit screens to call FastAPI."""

import os
from urllib.parse import quote

import requests

API_URL = os.getenv("INSULIN_API_URL", "http://127.0.0.1:8000/api")


class APIError(Exception):
    """A readable error returned by the FastAPI service."""


def request(method, path, token=None, data=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = requests.request(
            method,
            f"{API_URL}{quote(path, safe='/')}",
            json=data,
            headers=headers,
            timeout=10,
        )
    except requests.RequestException as error:
        raise APIError("The FastAPI server is not running. Start it in a separate terminal.") from error

    if not response.ok:
        try:
            message = response.json().get("detail", response.text)
        except ValueError:
            message = response.text
        raise APIError(str(message))
    return response.json() if response.content else None


def get(path, token=None):
    return request("GET", path, token)


def post(path, token=None, data=None):
    return request("POST", path, token, data)


def put(path, token=None, data=None):
    return request("PUT", path, token, data)


def delete(path, token=None):
    return request("DELETE", path, token)
