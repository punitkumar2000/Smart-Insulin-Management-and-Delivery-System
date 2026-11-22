import streamlit as st
from html import escape

from app_constants import DIABETES_TYPES
from api_client import APIError, post
from circular_buffer import CircularBuffer
from insulin_manager import remaining_days
from min_heap import MinHeap

def _render_table(rows, accessible_label):
    if not rows:
        return
    columns = list(dict.fromkeys(key for row in rows for key in row))
    header = "".join(f"<th>{escape(str(column))}</th>" for column in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(row.get(column, '')))}</td>" for column in columns) + "</tr>"
        for row in rows
    )
    st.markdown(
        f"""<div role="region" aria-label="{escape(accessible_label)}" style="overflow-x:auto; width:100%;">
        <table style="border-collapse:collapse; width:100%; min-width:850px; color:inherit;">
        <thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>
        <style>
        table th, table td {{ padding:0.55rem 0.7rem; text-align:left; border-bottom:1px solid rgba(128,128,128,.35); }}
        table th {{ background:rgba(128,128,128,.18); font-weight:600; }}
        </style>""",
        unsafe_allow_html=True,
    )


def _send_ntfy_reminder(patient_id, kind, token):
    try:
        post(f"/patients/{patient_id}/reminders/{kind}", token)
        st.success("ntfy accepted the reminder. Check the subscribed phone.")
    except APIError as error:
        st.error(f"ntfy did not send: {error}")


def _days(patient, consumption):
    buffer = CircularBuffer(consumption.get("values", []), consumption.get("index", 0))
    return remaining_days(patient["units_available"], buffer.average)


def _priority_patients(patients, consumption):
    heap = MinHeap()
    for patient_id, patient in patients.items():
        heap.push(_days(patient, consumption.get(patient_id, {})), (patient_id, patient))
    result = []
    while heap.items:
        days, (patient_id, patient) = heap.pop()
        result.append((days, patient_id, patient))
    return result


def _order_key(order):
    try:
        sequence = int(order.get("order_id", "").split("-")[-1])
    except ValueError:
        sequence = 0
    return (order.get("order_date", ""), sequence)


def _render_order_progress(order):
    labels = ["Order Accepted", "Insulin Shipped", "Order Dispatched", "Order Delivered"]
    current = {
        "Order Placed": 0,
        "Order Confirmed": 0,
        "Insulin Shipped": 1,
        "Out for Delivery": 2,
        "Delivered": 3,
        "Received and Confirmed by Patient": 3,
    }.get(order.get("status"), 0)
    columns = st.columns(4)
    for index, (column, label) in enumerate(zip(columns, labels)):
        if index < current:
            column.markdown(f"✅ **{label}**")
        elif index == current:
            column.markdown(f"🔵 **{label}**")
        else:
            column.markdown(f"⚪ {label}")


def render(user, data, token):
    st.markdown(
        f"<h2 style='font-size:1.85rem; line-height:1.2; margin:0 0 .5rem 0'>Medical Dashboard · {user.get('name', 'Medical Officer')}</h2>",
        unsafe_allow_html=True,
    )
    section = st.sidebar.radio(
        "Medical navigation",
        ["Dashboard", "Inventory Management", "Delivery Management", "Notification Management"],
    )
    patients = data["patients"]

    if section == "Dashboard":
        st.subheader("Patient supply priority")
        summary_columns = st.columns(5)
        summary_columns[0].metric("Number of patients", len(patients))
        inventory_by_type = {}
        for supplier_stock in data["inventory"].values():
            for diabetes_type, quantity in supplier_stock.items():
                inventory_by_type[diabetes_type] = (
                    inventory_by_type.get(diabetes_type, 0) + int(quantity)
                )
        for column, diabetes_type in zip(summary_columns[1:], DIABETES_TYPES):
            units = inventory_by_type.get(diabetes_type, 0)
            column.metric(f"{diabetes_type} · insulin", f"{units:,.0f} units")
        st.caption("Inventory totals update when a new lot is added or an order is shipped.")
        st.caption("Patients are automatically sorted by estimated days of insulin remaining; fewer days appear first.")

        rows = []
        for priority, (days, patient_id, patient) in enumerate(
            _priority_patients(patients, data["consumption"]), start=1
        ):
            rows.append({
                "Priority": priority,
                "Patient": patient["name"],
                "Patient ID": patient_id,
                "Age": patient.get("age", "—"),
                "Diabetes type": patient.get("diabetes_type", "Type 2 diabetes"),
                "Units available": patient["units_available"],
                "Days remaining": "∞" if days == float("inf") else round(days, 1),
                "Contact number": patient["contact"],
            })
        _render_table(rows, "Patient supply priority")

    elif section == "Inventory Management":
        st.subheader("Insulin inventory")
        supplier_key = next(iter(data["inventory"]), "Pune Care Pharmacy")
        inventory = data["inventory"].setdefault(supplier_key, {})
        for row_index, diabetes_type in enumerate(DIABETES_TYPES):
            with st.container(border=True):
                row_key=f"inventory_lot_{row_index}"
                with st.form(row_key):
                    type_col, available_col, lot_col, save_col = st.columns([1.8, 1.2, 1.4, 0.8])
                    type_col.markdown(f"**{diabetes_type}**")
                    type_col.caption("Insulin stock")
                    available_col.metric("Available units", f"{int(inventory.get(diabetes_type, 0)):,}")
                    new_lot = lot_col.number_input(
                        "Add new lot (units)", min_value=0, max_value=1_000_000,
                        value=0, step=10,
                        key=f"inventory_new_lot_{row_index}_{int(inventory.get(diabetes_type, 0))}"
                    )
                    submitted = save_col.form_submit_button("Add lot", type="primary")
                if submitted:
                    if new_lot < 1:
                        st.error("Enter the number of units in the new lot.")
                    else:
                        try:
                            post(f"/inventory/{diabetes_type}/lots", token, {"units": int(new_lot)})
                            st.rerun()
                        except APIError as error:
                            st.error(str(error))

    elif section == "Delivery Management":
        st.subheader("Order management")
        active_orders = sorted(
            [o for o in data["deliveries"] if o["status"] not in ("Rejected", "Delivered", "Received and Confirmed by Patient")],
            key=_order_key,
        )
        if not active_orders:
            st.info("There are no orders awaiting delivery.")
        for order_number, order in enumerate(active_orders, start=1):
            patient = patients.get(order["patient_id"], {})
            with st.container(border=True):
                st.markdown(f"### Order {order_number} · {order['order_id']}")
                details = st.columns(4)
                details[0].markdown(f"**Patient**  \n{patient.get('name', order['patient_id'])}")
                order_type = order.get("diabetes_type") or patient.get("diabetes_type") or order.get("insulin_type", "—")
                details[1].markdown(f"**Insulin type**  \n{order_type}")
                details[2].markdown(f"**Contact number**  \n{patient.get('contact', '—')}")
                details[3].markdown(f"**Units requested**  \n{int(order.get('quantity', 0))}")
                st.markdown(f"**Patient ID:** {order['patient_id']}  \n**Delivery address:** {patient.get('address', '—')}")
                _render_order_progress(order)

                if order["status"] in ("Order Placed", "Order Confirmed"):
                    accept_col, reject_col = st.columns([1, 1])
                    if accept_col.button("Accept & Ship Order", key=f"accept_ship_{order['order_id']}", type="primary"):
                        try:
                            post(f"/orders/{order['order_id']}/accept", token)
                            st.rerun()
                        except APIError as error:
                            st.error(str(error))
                    if reject_col.button("Reject order", key=f"reject_{order['order_id']}"):
                        try:
                            post(f"/orders/{order['order_id']}/reject", token)
                            st.rerun()
                        except APIError as error:
                            st.error(str(error))
                elif order["status"] == "Insulin Shipped":
                    if st.button("Mark Order Dispatched", key=f"dispatch_{order['order_id']}"):
                        try:
                            post(f"/orders/{order['order_id']}/dispatch", token)
                            st.rerun()
                        except APIError as error:
                            st.error(str(error))
                elif order["status"] == "Out for Delivery":
                    if st.button("Mark Order Delivered", key=f"delivered_{order['order_id']}"):
                        try:
                            post(f"/orders/{order['order_id']}/deliver", token)
                            st.rerun()
                        except APIError as error:
                            st.error(str(error))

        st.subheader("Order History")
        completed_orders = sorted(
            [o for o in data["deliveries"] if o["status"] in ("Delivered", "Received and Confirmed by Patient")],
            key=_order_key,
        )
        if completed_orders:
            history_rows = []
            for number, order in enumerate(completed_orders, start=1):
                patient = patients.get(order["patient_id"], {})
                history_rows.append({
                    "Order": number,
                    "Order ID": order["order_id"],
                    "Patient": patient.get("name", order["patient_id"]),
                    "Insulin type": order.get("diabetes_type") or patient.get("diabetes_type") or order.get("insulin_type", "—"),
                    "Units": order.get("quantity", 0),
                    "Order date": order.get("order_date", "—"),
                    "Status": order["status"],
                    "Contact number": patient.get("contact", "—"),
                    "Address": patient.get("address", "—"),
                })
            _render_table(history_rows, "Delivered order history")
        else:
            st.info("Delivered orders will appear here.")

    elif section == "Notification Management":
        st.subheader("Phone push reminders with ntfy")
        topic = data["settings"]["ntfy_topic"]
        st.markdown("1. Install the **ntfy** app on your phone.\n2. Subscribe to this random topic in the app:")
        st.code(topic)
        st.link_button("Open ntfy web app", "https://ntfy.sh/app")
        st.caption("Anyone who learns this topic can subscribe to it or publish to it. Keep it private. Push messages are generic and do not include patient names or medical details.")
        patient_id = st.selectbox("Patient to remind", list(patients), format_func=lambda x: f"{x} — {patients[x]['name']}")
        if st.button("Send first consumption reminder"):
            _send_ntfy_reminder(patient_id, "missed", token)
        if st.button("Send second reminder"):
            _send_ntfy_reminder(patient_id, "missed_second", token)
        if st.button("Send urgent reminder to patient"):
            _send_ntfy_reminder(patient_id, "missed_escalation", token)

