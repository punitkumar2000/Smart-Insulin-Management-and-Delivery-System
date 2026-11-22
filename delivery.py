"""Create a patient's delivery request while preventing duplicates."""
from datetime import date

def create_order(deliveries, patient, quantity):
    active_statuses = ("Rejected", "Received and Confirmed by Patient")
    if any(
        order["patient_id"] == patient["patient_id"] and order["status"] not in active_statuses
        for order in deliveries
    ):
        return None
    diabetes_type = patient.get("diabetes_type", "Type 2 diabetes")
    order = {
        "order_id": f"ORD-{date.today():%y%m%d}-{len(deliveries) + 1:04d}",
        "patient_id": patient["patient_id"],
        "insulin_type": diabetes_type,
        "diabetes_type": diabetes_type,
        "order_date": date.today().isoformat(),
        "quantity": int(quantity),
        "status": "Order Placed",
    }
    deliveries.append(order)
    return order
