"""The work performed by patient API actions."""

from datetime import date
from math import isfinite

from fastapi import HTTPException

from app_constants import DIABETES_TYPES, MAX_PATIENT_STOCK
from backend_helpers import find_order, find_patient
from circular_buffer import CircularBuffer
from delivery import create_order
from insulin_manager import remaining_days
from notifications import notify
from pickle_database import get_all, save_many, update
from pickle_storage import log_event


def get_dashboard(patient_id):
    data = get_all()
    find_patient(data, patient_id)
    return {
        "patients": {patient_id: data["patients"][patient_id]},
        "consumption": {patient_id: data["consumption"].get(patient_id, {})},
        "deliveries": [order for order in data["deliveries"] if order["patient_id"] == patient_id],
    }


def update_profile(patient_id, details):
    try:
        dob = date.fromisoformat(details.date_of_birth)
    except ValueError:
        raise HTTPException(status_code=400, detail="Enter a valid date of birth.")
    if dob < date(1950, 1, 1) or dob > date.today():
        raise HTTPException(status_code=400, detail="Date of birth must be between 1 January 1950 and today.")
    if details.diabetes_type not in DIABETES_TYPES:
        raise HTTPException(status_code=400, detail="Choose one of the listed diabetes types.")

    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    patient = update("patients", patient_id, {
        "name": details.name.strip(), "date_of_birth": dob.isoformat(), "age": age,
        "diabetes_type": details.diabetes_type, "address": details.address.strip(),
        "contact": details.contact.strip(), "emergency_contact": details.emergency_contact.strip(),
    })
    data = get_all()
    log_event(data["history"], patient_id, "Profile updated", f"Date of birth saved; calculated age {age}")
    save_many(history=data["history"])
    return patient


def save_consumption(patient_id, units):
    data = get_all()
    patient = find_patient(data, patient_id)
    stock_before = float(patient["units_available"])
    if units > stock_before:
        raise HTTPException(status_code=400, detail="Consumption exceeds available insulin.")

    readings = data["consumption"].setdefault(patient_id, {"values": [], "index": 0, "history": []})
    buffer = CircularBuffer(readings.get("values", []), readings.get("index", 0))
    buffer.add(units)
    readings["values"], readings["index"] = buffer.values, buffer.index
    readings.setdefault("history", []).append({
        "date": date.today().isoformat(), "units": units, "stock_deducted": True,
    })
    patient["units_available"] = stock_before - units
    patient["daily_consumption"] = buffer.average
    days = remaining_days(patient["units_available"], buffer.average)
    log_event(data["history"], patient_id, "Consumption updated", f"{units:g} units")
    log_event(data["history"], patient_id, "Insulin stock updated", f"{stock_before:g} → {patient['units_available']:g} units")
    log_event(data["history"], patient_id, "Supply estimate updated", f"{days:.1f} days remaining")
    save_many(consumption=data["consumption"], patients=data["patients"], history=data["history"])
    return {
        "units_available": patient["units_available"],
        "average": buffer.average,
        "days_remaining": days if isfinite(days) else None,
    }


def check_supply_alert(patient_id):
    data = get_all()
    patient = find_patient(data, patient_id)
    readings = data["consumption"].get(patient_id, {})
    buffer = CircularBuffer(readings.get("values", []), readings.get("index", 0))
    days = remaining_days(patient["units_available"], buffer.average)
    active_order = any(
        order["patient_id"] == patient_id
        and order["status"] not in ("Rejected", "Received and Confirmed by Patient")
        for order in data["deliveries"]
    )
    if days > 7 or buffer.average <= 0 or active_order:
        return {"sent": False}

    kind, today = ("critical" if days <= 5 else "low"), date.today().isoformat()
    sent_today = any(
        item.get("patient_id") == patient_id and item.get("type") == kind and item.get("date") == today
        for item in data["notifications"]
    )
    if sent_today:
        return {"sent": False}

    notify(data["notifications"], data["history"], patient, kind, f"Estimated {days:.1f} days remaining.")
    save_many(notifications=data["notifications"], history=data["history"])
    return {"sent": True}


def place_order(patient_id, units):
    data = get_all()
    patient = find_patient(data, patient_id)
    space = max(0, MAX_PATIENT_STOCK - float(patient["units_available"]))
    if units > space:
        raise HTTPException(status_code=400, detail=f"You can store up to {space} more units.")
    order = create_order(data["deliveries"], patient, units)
    if not order:
        raise HTTPException(status_code=409, detail="An insulin order is already active for your account.")
    patient["last_patient_manual_order_id"] = order["order_id"]
    log_event(data["history"], patient_id, "Manual delivery request", f"{order['order_id']} · {units} units")
    save_many(deliveries=data["deliveries"], patients=data["patients"], history=data["history"])
    return order


def confirm_delivery(order_id, user):
    data = get_all()
    order = find_order(data, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if user["role"] != "patient" or user["id"] != order["patient_id"]:
        raise HTTPException(status_code=403, detail="This patient account cannot access that record.")
    if order["status"] != "Delivered":
        raise HTTPException(status_code=409, detail="The order is not marked delivered yet.")

    patient = find_patient(data, order["patient_id"])
    before = float(patient["units_available"])
    received = min(int(order["quantity"]), max(0, MAX_PATIENT_STOCK - int(before)))
    patient["units_available"] = before + received
    order["status"] = "Received and Confirmed by Patient"
    log_event(data["history"], order["patient_id"], "Delivery confirmed", order_id)
    log_event(data["history"], order["patient_id"], "Insulin stock replenished", f"{before:g} → {patient['units_available']:g} units")
    save_many(patients=data["patients"], deliveries=data["deliveries"], history=data["history"])
    return {"units_available": patient["units_available"]}
