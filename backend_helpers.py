"""A few shared helpers for API routes."""

import inspect
import json
from functools import wraps

from fastapi import HTTPException, Request

from auth import user_from_id
from pickle_database import get, get_all

_PRIVATE_FIELDS = {
    "address", "contact", "date_of_birth", "emergency_contact", "name",
    "ntfy_topic", "password", "recipient", "token", "authorization",
}


def _safe_log(value):
    """Convert request/response data to JSON and hide private fields."""
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if isinstance(value, dict):
        return {
            key: "[hidden]" if key.lower() in _PRIVATE_FIELDS else _safe_log(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_safe_log(item) for item in value]
    return value


def trace_api(route_name):
    """Print one readable, privacy-filtered line for an API call."""
    def decorate(function):
        @wraps(function)
        def run(*args, **kwargs):
            values = inspect.signature(function).bind_partial(*args, **kwargs).arguments
            request_data = {key: value for key, value in values.items() if key != "request"}
            print(f"[API] {route_name} input={json.dumps(_safe_log(request_data), default=str)}", flush=True)
            try:
                result = function(*args, **kwargs)
            except HTTPException as error:
                print(f"[API] {route_name} error={error.status_code}: {error.detail}", flush=True)
                raise
            except Exception as error:
                print(f"[API] {route_name} error={type(error).__name__}: {error}", flush=True)
                raise
            print(f"[API] {route_name} output={json.dumps(_safe_log(result), default=str)}", flush=True)
            return result

        return run
    return decorate


def session_token(request: Request):
    """Read the token from the Authorization: Bearer header."""
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Please sign in again.")
    return token


def current_user(request: Request):
    """Find the signed-in user using the saved session token."""
    token = session_token(request)
    session = get("sessions", token)
    if not session:
        raise HTTPException(status_code=401, detail="Please sign in again.")

    data = get_all()
    user = user_from_id(session.get("id"), data["patients"], data["medical_users"])
    if not user:
        raise HTTPException(status_code=401, detail="This login session is no longer valid.")
    return user


def patient_user(request: Request, patient_id: str):
    """Allow a patient to access only their own records."""
    user = current_user(request)
    if user["role"] != "patient" or user["id"] != patient_id:
        raise HTTPException(status_code=403, detail="This patient account cannot access that record.")
    return user


def medical_user(request: Request):
    """Allow only a medical officer to use medical routes."""
    user = current_user(request)
    if user["role"] != "medical":
        raise HTTPException(status_code=403, detail="Medical officer access is required.")
    return user


def find_patient(data, patient_id: str):
    patient = data["patients"].get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    return patient


def find_order(data, order_id: str):
    return next((order for order in data["deliveries"] if order["order_id"] == order_id), None)
