"""Record care reminders and optionally send a generic ntfy push notification."""
from datetime import date

from ntfy import send_ntfy_message


def notify(notifications, history, patient, kind, detail="", send_push=False, topic=""):
    templates = {
        "missed": "Reminder: Please follow your prescribed insulin plan and update your usage in the care dashboard.",
        "missed_second": "Second reminder: Please follow your prescribed insulin plan and update your usage in the care dashboard.",
        "missed_escalation": "Urgent reminder: Please follow your prescribed insulin plan. Open the care dashboard to update your usage.",
        "low": f"Supply reminder: insulin supply is low. {detail}",
        "critical": f"Urgent supply reminder: insulin supply is critical. Please contact your care team. {detail}",
        "shipped": f"Your insulin order has shipped. {detail}",
        "delivered": "Your insulin delivery is marked delivered. Please confirm receipt.",
    }
    message = templates.get(kind, detail or kind)
    result = {"status": "recorded", "detail": "Saved locally; push notification was not requested."}
    if send_push:
        result = send_ntfy_message(topic, message)

    notifications.append({
        "date": date.today().isoformat(),
        "patient_id": patient["patient_id"],
        "type": kind,
        "recipient": topic if send_push else patient.get("contact", ""),
        "message": message,
        "channel": "ntfy" if result["status"] == "sent" else "ntfy unavailable" if send_push else "Simulation",
        "send_status": result["status"],
        "message_id": result.get("message_id", ""),
    })
    event = "ntfy reminder sent" if result["status"] == "sent" else "Notification: " + kind
    history.append({"date": date.today().isoformat(), "patient_id": patient["patient_id"], "event": event, "details": message})
    return result
