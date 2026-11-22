# Smart Insulin Management and Delivery System

The project has a Streamlit website, a FastAPI backend, and local pickle data.

## Run the project

Install packages once:

```powershell
python -m pip install -r requirements.txt
```

Run this one command in PowerShell from this folder:

```powershell
python -m uvicorn api:app --reload --port 8000
```

It starts FastAPI and the Streamlit website together. Open the website at `http://localhost:8000`; the API guide is at `http://localhost:8000/docs`.

The terminal prints each API method, route, request fields, and response. Passwords, session tokens, and private profile/contact fields are hidden in those log entries.

Sample logins: patients `P001`–`P006` / `patient123`; medical officer `M001` / `care123`.

## Project files

| File | Purpose |
|---|---|
| `main.py` | Starts the Streamlit website and selects the right screen. |
| `patient_frontend.py` | Patient screen: profile, consumption graph, and orders. |
| `medical_ui.py` | Medical officer screen: priority list, inventory, orders, and reminders. |
| `api.py` | Starts FastAPI and handles login and shared sessions. |
| `patient_backend_api.py` | Patient API addresses and the fields each request accepts. |
| `patient_actions.py` | The work behind patient requests, such as saving insulin use or placing an order. |
| `medical_backend_api.py` | Medical API addresses and the fields each request accepts. |
| `medical_actions.py` | The work behind inventory, delivery, and reminder requests. |
| `backend_helpers.py` | Checks who is signed in and what they may access. |
| `api_client.py` | Sends requests from Streamlit to FastAPI. |
| `pickle_database.py` | Simple `get`, `add`, `update`, and `delete` helpers. |
| `pickle_storage.py` | Reads/writes pickle files, creates demo data, and updates older data. |
| `app_constants.py` | Shared diabetes type options and the patient stock limit. |
| `circular_buffer.py` | Keeps the latest five consumption readings. |
| `min_heap.py` | Sorts patients so the lowest supply estimate appears first. |
| `insulin_manager.py` | Calculates supply days and warning levels. |
| `delivery.py` | Creates delivery orders. |
| `notifications.py`, `ntfy.py` | Records reminders and sends ntfy push messages. |
| `data/` | Saved patient, inventory, order, and settings files. Keep these files to retain local data. |

## A few terms

- **API route**: an address the website calls to request an action or data.
- **Request model**: the fields an API action accepts. For example, `ProfileInput` lists the profile fields. These are kept beside the API that uses them.
- **Action**: the work done after an API route receives a request. For example, `patient_actions.py` subtracts insulin use and updates the average.
- **Pickle**: the local file format used to save this demo's data.
- **Circular buffer**: the five-reading rolling window used for the insulin average.
- **Min heap**: the data structure used to put patients with fewer supply days first.

For example, the patient website sends today's use to the patient API route. The route checks the patient and calls `patient_actions.py`, which updates the circular buffer and stock and saves through `pickle_database.py` and `pickle_storage.py`.

Pickle files are for trusted local data only. This demo tracks supply and delivery; it does not calculate treatment doses or replace clinician instructions.
