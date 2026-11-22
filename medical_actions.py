"""The work performed by medical officer API actions."""

import secrets

from fastapi import HTTPException

from app_constants import DIABETES_TYPES
from backend_helpers import find_order, find_patient
from notifications import notify
from pickle_database import get_all, save_many
from pickle_storage import log_event


def get_dashboard():
    data = get_all()
    topic = data["settings"].get("ntfy_topic")
    if not topic:
        topic = "insulin-care-" + secrets.token_hex(16)
        data["settings"]["ntfy_topic"] = topic
        save_many(settings=data["settings"])
    return {
        "patients": data["patients"], "consumption": data["consumption"],
        "inventory": data["inventory"], "deliveries": data["deliveries"],
        "settings": {"ntfy_topic": topic},
    }


def add_inventory_lot(diabetes_type, units):
    if diabetes_type not in DIABETES_TYPES:
        raise HTTPException(status_code=404, detail="Insulin type not found.")
    data = get_all()
    supplier = next(iter(data["inventory"]), "Pune Care Pharmacy")
    stock = data["inventory"].setdefault(supplier, {})
    stock[diabetes_type] = int(stock.get(diabetes_type, 0)) + units
    log_event(data["history"], "", "Insulin lot added", f"{diabetes_type}: +{units} units; total {stock[diabetes_type]} units")
    save_many(inventory=data["inventory"], history=data["history"])
    return {"available_units": stock[diabetes_type]}


def update_order(order_id, action):
    data = get_all()
    order = find_order(data, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    patient = find_patient(data, order["patient_id"])

    if action == "accept":
        _ship_order(data, order, patient, order_id)
    elif action == "reject" and order["status"] in ("Order Placed", "Order Confirmed"):
        order.update(status="Rejected", notes="Rejected by the medical officer.")
        log_event(data["history"], order["patient_id"], "Order rejected", order_id)
    elif action == "dispatch" and order["status"] == "Insulin Shipped":
        order["status"] = "Out for Delivery"
        log_event(data["history"], order["patient_id"], "Order dispatched", order_id)
    elif action == "deliver" and order["status"] == "Out for Delivery":
        order["status"] = "Delivered"
        notify(data["notifications"], data["history"], patient, "delivered")
        log_event(data["history"], order["patient_id"], "Order delivered", order_id)
    else:
        raise HTTPException(status_code=409, detail="That action is not valid for this order status.")

    save_many(deliveries=data["deliveries"], notifications=data["notifications"], history=data["history"])
    return order


def _ship_order(data, order, patient, order_id):
    if order["status"] not in ("Order Placed", "Order Confirmed"):
        raise HTTPException(status_code=409, detail="This order cannot be shipped from its current status.")
    insulin_type = order.get("diabetes_type") or patient.get("diabetes_type", "")
    supplier = next(iter(data["inventory"]), None)
    inventory = data["inventory"].get(supplier, {}) if supplier else {}
    quantity = int(order.get("quantity", 0))
    available = int(inventory.get(insulin_type, 0))
    if available < quantity:
        raise HTTPException(status_code=409, detail=f"Not enough {insulin_type} in inventory. Available: {available} units.")

    inventory[insulin_type] = available - quantity
    order.update(diabetes_type=insulin_type, insulin_type=insulin_type, status="Insulin Shipped")
    notify(data["notifications"], data["history"], patient, "shipped", f"Order {order_id}.")
    log_event(data["history"], order["patient_id"], "Order accepted and shipped", f"{order_id} · {quantity} units")
    save_many(inventory=data["inventory"])


def send_reminder(patient_id, kind):
    if kind not in ("missed", "missed_second", "missed_escalation"):
        raise HTTPException(status_code=404, detail="Reminder type not found.")
    data = get_all()
    patient = find_patient(data, patient_id)
    topic = data["settings"].get("ntfy_topic")
    if not topic:
        topic = "insulin-care-" + secrets.token_hex(16)
        data["settings"]["ntfy_topic"] = topic
        save_many(settings=data["settings"])
    result = notify(data["notifications"], data["history"], patient, kind, send_push=True, topic=topic)
    save_many(notifications=data["notifications"], history=data["history"])
    if result["status"] != "sent":
        raise HTTPException(status_code=502, detail=result["detail"])
    return {"message": "ntfy accepted the reminder."}
