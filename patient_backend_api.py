"""Patient API addresses and request fields."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend_helpers import current_user, patient_user, trace_api
from patient_actions import (
    check_supply_alert,
    confirm_delivery,
    get_dashboard,
    place_order,
    save_consumption,
    update_profile,
)

router = APIRouter()


class ProfileInput(BaseModel):
    name: str
    date_of_birth: str
    diabetes_type: str
    address: str
    contact: str
    emergency_contact: str


class ConsumptionInput(BaseModel):
    units: float = Field(ge=0, le=500)


class OrderInput(BaseModel):
    units: int = Field(gt=0)


@router.get("/patients/{patient_id}/dashboard")
@trace_api("GET /api/patients/{patient_id}/dashboard")
def patient_dashboard(patient_id: str, request: Request):
    patient_user(request, patient_id)
    return get_dashboard(patient_id)


@router.put("/patients/{patient_id}/profile")
@trace_api("PUT /api/patients/{patient_id}/profile")
def patient_profile(patient_id: str, details: ProfileInput, request: Request):
    patient_user(request, patient_id)
    return update_profile(patient_id, details)


@router.post("/patients/{patient_id}/consumption")
@trace_api("POST /api/patients/{patient_id}/consumption")
def patient_consumption(patient_id: str, details: ConsumptionInput, request: Request):
    patient_user(request, patient_id)
    return save_consumption(patient_id, details.units)


@router.post("/patients/{patient_id}/check-supply-alert")
@trace_api("POST /api/patients/{patient_id}/check-supply-alert")
def patient_supply_alert(patient_id: str, request: Request):
    patient_user(request, patient_id)
    return check_supply_alert(patient_id)


@router.post("/patients/{patient_id}/orders")
@trace_api("POST /api/patients/{patient_id}/orders")
def patient_order(patient_id: str, details: OrderInput, request: Request):
    patient_user(request, patient_id)
    return place_order(patient_id, details.units)


@router.post("/orders/{order_id}/confirm")
@trace_api("POST /api/orders/{order_id}/confirm")
def patient_confirm_order(order_id: str, request: Request):
    return confirm_delivery(order_id, current_user(request))
