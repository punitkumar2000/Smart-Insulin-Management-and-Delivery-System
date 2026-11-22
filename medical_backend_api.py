"""Medical officer API addresses and request fields."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend_helpers import medical_user, trace_api
from medical_actions import add_inventory_lot, get_dashboard, send_reminder, update_order

router = APIRouter()


class InventoryLotInput(BaseModel):
    units: int = Field(gt=0)


@router.get("/medical/dashboard")
@trace_api("GET /api/medical/dashboard")
def medical_dashboard(request: Request):
    medical_user(request)
    return get_dashboard()


@router.post("/inventory/{diabetes_type}/lots")
@trace_api("POST /api/inventory/{diabetes_type}/lots")
def inventory_lot(diabetes_type: str, details: InventoryLotInput, request: Request):
    medical_user(request)
    return add_inventory_lot(diabetes_type, details.units)


@router.post("/orders/{order_id}/{action}")
@trace_api("POST /api/orders/{order_id}/{action}")
def medical_order(order_id: str, action: str, request: Request):
    medical_user(request)
    return update_order(order_id, action)


@router.post("/patients/{patient_id}/reminders/{kind}")
@trace_api("POST /api/patients/{patient_id}/reminders/{kind}")
def medical_reminder(patient_id: str, kind: str, request: Request):
    medical_user(request)
    return send_reminder(patient_id, kind)
