"""Demo authentication and role lookup."""
def authenticate(username, password, patients, medical_users):
    for pid, p in patients.items():
        if username.strip().lower() in (pid.lower(), p["name"].lower()) and password == "patient123" or password == "patient112233":
            return {"id": pid, "role": "patient", **p}
    user = medical_users.get(username.strip().upper())
    if user and user["password"] == password:
        return {**user, "id": user["user_id"]}
    return None

def user_from_id(user_id, patients, medical_users):
    """Restore the signed-in user's role after a browser refresh."""
    if user_id in patients:
        patient = patients[user_id]
        return {"id": user_id, "role": "patient", "name": patient["name"]}
    user = medical_users.get(str(user_id).upper())
    if user:
        return {"id": user["user_id"], "role": user["role"], "name": user["name"]}
    return None
