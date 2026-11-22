"""Run the FastAPI backend and the Streamlit website on one server."""

import logging
from pathlib import Path
from secrets import token_urlsafe

import streamlit as st
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from auth import authenticate
from backend_helpers import current_user, session_token, trace_api
from medical_backend_api import router as medical_routes
from patient_backend_api import router as patient_routes
from pickle_database import add, delete, get_all


class LoginInput(BaseModel):
    username: str
    password: str

streamlit_app = st.App(str(Path(__file__).with_name("main.py")))
app = FastAPI(
    title="Smart Insulin Management API",
    lifespan=streamlit_app.lifespan(),
)
app.include_router(patient_routes, prefix="/api")
app.include_router(medical_routes, prefix="/api")


@app.get("/api/health")
@trace_api("GET /api/health")
def health():
    return {"status": "ok"}


@app.post("/api/login")
@trace_api("POST /api/login")
def login(details: LoginInput):
    data = get_all()
    user = authenticate(details.username, details.password, data["patients"], data["medical_users"])
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect ID or password.")

    user.pop("password", None)
    token = token_urlsafe(32)
    add("sessions", {"id": user["id"], "role": user["role"]}, key=token)
    return {"token": token, "user": user}


@app.get("/api/session")
@trace_api("GET /api/session")
def session(request: Request):
    return current_user(request)


@app.delete("/api/session")
@trace_api("DELETE /api/session")
def logout(request: Request):
    delete("sessions", session_token(request))
    return {"message": "Signed out."}


# Add the website last so it does not intercept API requests.
app.mount("/", streamlit_app)

# The trace_api decorator prints useful API details; disable duplicate access lines.
logging.getLogger("uvicorn.access").disabled = True
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("websockets.server").setLevel(logging.WARNING)
