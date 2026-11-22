"""Send generic push notifications through ntfy's public HTTP API."""
from urllib.parse import quote
import requests


def send_ntfy_message(topic, message):
    if not topic:
        return {"status": "not_configured", "detail": "No ntfy topic is configured."}

    url = f"https://ntfy.sh/{quote(topic, safe='')}"
    try:
        response = requests.post(
            url,
            data=message.encode("utf-8"),
            headers={"Title": "Care dashboard reminder"},
            timeout=15,
        )
    except requests.RequestException as exc:
        return {"status": "failed", "detail": f"Could not reach ntfy: {exc}"}

    if not response.ok:
        return {"status": "failed", "detail": f"ntfy returned HTTP {response.status_code}."}
    return {"status": "sent", "detail": "ntfy accepted the push notification."}
