"""Pickle-only persistence. Seed files are created on first launch."""
import os
import pickle
import random
from datetime import date

from app_constants import DIABETES_TYPES

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FILES = {name: os.path.join(DATA_DIR, name + ".pkl") for name in
         ("patients", "medical_users", "inventory", "consumption", "deliveries", "notifications", "history", "sessions", "settings")}

def _seed():
    patients = {}
    names = ["Aarav Mehta", "Maya Singh", "Rohan Patel", "Anika Sharma", "Kabir Rao", "Isha Nair"]
    for i, name in enumerate(names, 1):
        pid = f"P{i:03d}"
        patients[pid] = {"patient_id": pid, "name": name, "age": 25 + i * 4, "address": f"{i} Lake View Road, Pune",
            "contact": f"+91 90000 100{i:02d}", "diabetes_type": "Type 2 diabetes", "insulin_type": "Rapid-acting" if i % 2 else "Long-acting",
            "daily_consumption": 10, "units_available": 100,
            "emergency_contact": f"+91 98888 200{i:02d}", "officer_id": "M001",
            "delivery_details": "Home delivery", "address_private": False}
    return {"patients": patients,
        "medical_users": {"M001": {"user_id":"M001", "name":"Dr. Vijay Katkar", "password":"care123", "role":"medical", "contact":"+91 90000 00001", "supplier":"Pune Care Pharmacy"}},
        "inventory": {"Pune Care Pharmacy": {"Rapid-acting": 1550, "Long-acting": 1500}},
        "consumption": {f"P{i:03d}": {"values":[10.0]*5, "index":0, "history":[]} for i in range(1,7)},
        "deliveries": [], "notifications": [], "history": [], "sessions": {}, "settings": {}}

def load_all():
    os.makedirs(DATA_DIR, exist_ok=True)
    seed = _seed()
    for key, path in FILES.items():
        if not os.path.exists(path): save(key, seed[key])
    data = {key: load(key) for key in FILES}
    changed = False
    for patient in data["patients"].values():
        if patient.get("diabetes_type") not in DIABETES_TYPES:
            patient["diabetes_type"] = "Type 2 diabetes"
            changed = True
        if "demo_auto_refill_to_120" in patient:
            patient.pop("demo_auto_refill_to_120",None)
            changed = True
    if changed:
        save("patients", data["patients"])
    medical_user=data["medical_users"].get("M001")
    if medical_user and medical_user.get("name") != "Dr. Vijay Katkar":
        medical_user["name"]="Dr. Vijay Katkar"
        save("medical_users",data["medical_users"])
    if not data["settings"].get("demo_diabetes_type_mix_v1"):
        demo_patient_ids=[f"P{i:03d}" for i in range(1,7) if f"P{i:03d}" in data["patients"]]
        assignments=(DIABETES_TYPES*((len(demo_patient_ids)+len(DIABETES_TYPES)-1)//len(DIABETES_TYPES)))[:len(demo_patient_ids)]
        random.shuffle(assignments)
        for patient_id, diabetes_type in zip(demo_patient_ids,assignments):
            data["patients"][patient_id]["diabetes_type"]=diabetes_type
        data["settings"]["demo_diabetes_type_mix_v1"]=True
        save("patients",data["patients"])
        save("settings",data["settings"])
    # Apply the requested demo baseline once to existing sample accounts while
    # preserving their profiles, delivery records, and event history.
    if not data["settings"].get("demo_baseline_100_units_v1"):
        today = date.today().isoformat()
        for pid in (f"P{i:03d}" for i in range(1, 7)):
            if pid not in data["patients"]:
                continue
            patient = data["patients"][pid]
            patient["units_available"] = 100
            patient["daily_consumption"] = 10
            consumption = data["consumption"].setdefault(pid, {"values": [], "index": 0, "history": []})
            consumption["values"] = [10.0] * 5
            consumption["index"] = 0
            today_entry = next((entry for entry in reversed(consumption["history"]) if entry.get("date") == today), None)
            if today_entry:
                today_entry.update(units=10.0, stock_deducted=False)
            log_event(data["history"], pid, "Demo baseline reset", "Supply set to 100 units and five-window consumption to 10 units/day")
        data["settings"]["demo_baseline_100_units_v1"] = True
        save("patients", data["patients"])
        save("consumption", data["consumption"])
        save("history", data["history"])
        save("settings", data["settings"])
    if not data["settings"].get("single_supplier_v1"):
        supplier_name="Pune Care Pharmacy"
        consolidated={}
        for supplier_stock in data["inventory"].values():
            for insulin_formulation,quantity in supplier_stock.items():
                consolidated[insulin_formulation]=consolidated.get(insulin_formulation,0)+int(quantity)
        data["inventory"]={supplier_name:consolidated}
        for user in data["medical_users"].values():
            user["supplier"]=supplier_name
        for patient in data["patients"].values():
            patient["supplier"]=supplier_name
        for order in data["deliveries"]:
            order["supplier"]=supplier_name
        data["settings"]["single_supplier_v1"]=True
        save("inventory",data["inventory"])
        save("medical_users",data["medical_users"])
        save("patients",data["patients"])
        save("deliveries",data["deliveries"])
        save("settings",data["settings"])
    if not data["settings"].get("single_medical_login_v1"):
        primary_id="M001"
        if primary_id not in data["medical_users"]:
            data["medical_users"][primary_id]=seed["medical_users"][primary_id]
        primary_user=data["medical_users"][primary_id]
        primary_user["supplier"]="Pune Care Pharmacy"
        data["medical_users"]={primary_id:primary_user}
        for patient in data["patients"].values():
            patient["officer_id"]=primary_id
        for notification in data["notifications"]:
            if notification.get("recipient")=="M002":
                notification["recipient"]=primary_id
        data["sessions"]={token:session for token,session in data["sessions"].items()
                          if session.get("id")!= "M002"}
        data["settings"]["single_medical_login_v1"]=True
        save("medical_users",data["medical_users"])
        save("patients",data["patients"])
        save("notifications",data["notifications"])
        save("sessions",data["sessions"])
        save("settings",data["settings"])
    return data

def load(key):
    path = FILES[key]
    with open(path, "rb") as f: return pickle.load(f)

def log_event(history, patient_id, event, details=""):
    history.append({"date": date.today().isoformat(), "patient_id": patient_id, "event": event, "details": details})


def save(key, value):
    os.makedirs(DATA_DIR, exist_ok=True)
    temp = FILES[key] + ".tmp"
    with open(temp, "wb") as f: pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(temp, FILES[key])
