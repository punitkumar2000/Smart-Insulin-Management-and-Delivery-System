"""Streamlit interface: login, top navigation, and dashboard selection."""

import sys

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

from api_client import APIError, delete, get, post
from medical_ui import render as medical_view
from patient_frontend import render as patient_view


if get_script_run_ctx(suppress_warning=True) is None:
    print("Start the app with: python -m streamlit run main.py")
    sys.exit(1)

st.set_page_config(page_title="Smart Insulin Management", page_icon="💙", layout="wide")
st.markdown(
    """<style>
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewContainer"] .main .block-container {
        padding-top: 0.75rem;
        padding-bottom: 0.75rem;
    }
    .st-key-top_nav {
        position: sticky;
        top: 0;
        z-index: 999;
        background: var(--background-color);
        padding: 0.25rem 0;
    }
    </style>""",
    unsafe_allow_html=True,
)


def show_login():
    st.title("💙 Smart Insulin Management & Delivery")
    st.caption("Patient care coordination")
    _, center, _ = st.columns([1, 1.15, 1])
    with center, st.container(border=True):
        st.subheader("LOGIN")
        with st.form("login"):
            username = st.text_input("ID")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign in", type="primary", width="stretch")
        if submit:
            try:
                result = post("/login", data={"username": username, "password": password})
                st.query_params["session"] = result["token"]
                st.rerun()
            except APIError as error:
                st.error(str(error))
        with st.expander("Sample login credentials"):
            st.markdown("**Patients:** P001–P006, password `patient123 or punit@123 or pranay@123`  \n**Medical officer:** M001 / `care123`")


def show_dashboard(user, token):
    with st.container(key="top_nav"):
        brand, profile_col, signout_col = st.columns([7, 1.7, 1.2], vertical_alignment="center", gap="small")
        brand.markdown("**💙 Smart Insulin Management & Delivery**")
        if user["role"] == "patient":
            on_profile = st.session_state.get("patient_page") == "profile"
            if profile_col.button("Dashboard" if on_profile else "My Profile"):
                st.session_state.patient_page = "dashboard" if on_profile else "profile"
                st.rerun()
        if signout_col.button("Sign out"):
            try:
                delete("/session", token)
            except APIError as error:
                st.warning(f"The browser session ended, but the server could not revoke it: {error}")
            if "session" in st.query_params:
                del st.query_params["session"]
            st.session_state.pop("patient_page", None)
            st.rerun()

    try:
        if user["role"] == "patient":
            data = get(f"/patients/{user['id']}/dashboard", token)
            patient_view(user["id"], data, token, show_profile=st.session_state.get("patient_page") == "profile")
        else:
            data = get("/medical/dashboard", token)
            medical_view(user, data, token)
    except APIError as error:
        st.error(str(error))


token = st.query_params.get("session")
if not token:
    show_login()
else:
    try:
        current_user = get("/session", token)
        show_dashboard(current_user, token)
    except APIError as error:
        if str(error) == "Please sign in again." or str(error) == "This login session is no longer valid.":
            del st.query_params["session"]
            st.rerun()
        st.error(str(error))
