import streamlit as st
import matplotlib.pyplot as plt
import calendar
from datetime import date
from app_constants import DIABETES_TYPES, MAX_PATIENT_STOCK
from api_client import APIError, post, put
from circular_buffer import CircularBuffer
from insulin_manager import remaining_days, threshold

def _age_from_dob(dob, today=None):
    if dob is None:
        return None
    today=today or date.today()
    return today.year-dob.year-((today.month,today.day)<(dob.month,dob.day))

def _render_manual_order_progress(order):
    st.markdown("**Delivery progress**")
    steps=["Order Placed","Order Shipped","Order Dispatched","Order Delivered"]
    status=order.get("status","Order Placed")
    current={"Order Placed":0,"Order Confirmed":0,"Insulin Shipped":1,
             "Out for Delivery":2,"Delivered":3,
             "Received and Confirmed by Patient":3}.get(status,0)
    cols=st.columns(4)
    for i,(col,label) in enumerate(zip(cols,steps)):
        if i < current:
            col.markdown(f"✅ **{label}**")
        elif i == current:
            col.markdown(f"🔵 **{label}**")
        else:
            col.markdown(f"⚪ {label}")

def render(pid, data, token, show_profile=False):
    p=data["patients"][pid]; c=data["consumption"].setdefault(pid,{"values":[],"index":0,"history":[]})
    buf=CircularBuffer(c["values"],c["index"]); avg=buf.average; days=remaining_days(p["units_available"],avg); label,color=threshold(days)
    if show_profile:
        st.title("My Profile")
        saved_dob=p.get("date_of_birth")
        try:
            dob_value=date.fromisoformat(saved_dob) if saved_dob else None
        except (TypeError,ValueError):
            dob_value=None
        name=st.text_input("Name",p["name"],key=f"profile_name_{pid}")
        today=date.today()
        st.markdown("**Date of birth**")
        year_col,month_col,day_col=st.columns(3)
        year_options=["Select year"]+list(range(1950,today.year+1))
        year_default=year_options.index(dob_value.year) if dob_value and 1950<=dob_value.year<=today.year else 0
        birth_year=year_col.selectbox("Year",year_options,index=year_default,key=f"profile_dob_year_{pid}")
        available_months=list(range(1,today.month+1)) if birth_year==today.year else list(range(1,13))
        month_options=["Select month"]+available_months
        month_default=month_options.index(dob_value.month) if dob_value and birth_year==dob_value.year and dob_value.month in available_months else 0
        birth_month=month_col.selectbox("Month",month_options,index=month_default,
            format_func=lambda value: value if isinstance(value,str) else calendar.month_name[value],key=f"profile_dob_month_{pid}_{birth_year}")
        dob=None
        if isinstance(birth_year,int) and isinstance(birth_month,int):
            max_day=calendar.monthrange(birth_year,birth_month)[1]
            if birth_year==today.year and birth_month==today.month:
                max_day=min(max_day,today.day)
            default_day=dob_value.day if dob_value and birth_year==dob_value.year and birth_month==dob_value.month else 1
            birth_day=day_col.number_input("Day",min_value=1,max_value=max_day,value=min(default_day,max_day),step=1,
                key=f"profile_dob_day_{pid}_{birth_year}_{birth_month}")
            dob=date(birth_year,birth_month,int(birth_day))
        else:
            day_col.selectbox("Day",["Select day"],key=f"profile_dob_day_empty_{pid}")
        calculated_age=_age_from_dob(dob)
        st.caption(f"Age: {calculated_age}" if calculated_age is not None else "Age: enter date of birth")
        with st.form("profile_form"):
            diabetes_type=st.selectbox("Diabetes type",DIABETES_TYPES,index=DIABETES_TYPES.index(p.get("diabetes_type","Type 2 diabetes")))
            address=st.text_input("Address",p["address"]); contact=st.text_input("Contact number",p["contact"])
            emergency=st.text_input("Emergency contact",p["emergency_contact"])
            save_profile=st.form_submit_button("Update profile")
        if save_profile:
            if dob is None:
                st.error("Please enter your date of birth so your age can be calculated.")
            else:
                try:
                    put(f"/patients/{pid}/profile", token, {
                        "name": name,
                        "date_of_birth": dob.isoformat(),
                        "diabetes_type": diabetes_type,
                        "address": address,
                        "contact": contact,
                        "emergency_contact": emergency,
                    })
                    st.success("Profile updated.")
                    st.rerun()
                except APIError as error:
                    st.error(str(error))
        return
    st.title(f"Welcome, {p['name']}")
    st.caption("Your care overview · data saved locally")
    a,b,d=st.columns(3); a.metric("Insulin available",f"{float(p['units_available']):,.1f} units"); b.metric("5-window daily average",f"{avg:.1f} units"); d.metric("Estimated supply", "No data" if avg==0 else f"{days:.1f} days")
    st.markdown(f"### Supply status: :{color}[{label}]")
    active_order=next((o for o in reversed(data["deliveries"]) if o["patient_id"]==pid and o["status"] not in ("Rejected","Received and Confirmed by Patient")),None)
    try:
        post(f"/patients/{pid}/check-supply-alert", token)
    except APIError as error:
        st.warning(str(error))
    st.subheader("Five consumption windows")
    chart_col, entry_col = st.columns([1.05, 1], gap="large")
    with chart_col:
        fig, ax = plt.subplots(figsize=(5, 3.4))
        plotted_values=buf.ordered_values
        x=list(range(len(plotted_values)))
        bars=ax.bar(x,plotted_values,width=0.42,color="#d94b4b")
        for bar,value in zip(bars,plotted_values):
            ax.annotate(f"{value:g} units",(bar.get_x()+bar.get_width()/2,bar.get_height()),
                        xytext=(0,4),textcoords="offset points",ha="center",va="bottom",fontsize=9)
        ax.margins(y=0.16)
        ax.set_xticks(x,[f"Day {i+1}" for i in x]); ax.set_ylabel("Insulin units")
        ax.set_title("Recent daily consumption"); ax.grid(axis="y",alpha=0.2); ax.set_axisbelow(True)
        fig.tight_layout(); st.pyplot(fig,width="stretch"); plt.close(fig)
    with entry_col:
        st.markdown("#### Enter today's insulin use")
        with st.form("consumption_form"):
            units=st.number_input("Insulin units consumed",min_value=0.0,max_value=500.0,value=float(p["daily_consumption"]),step=0.5)
            submitted=st.form_submit_button("Save consumption")
        if submitted:
            try:
                post(f"/patients/{pid}/consumption", token, {"units": units})
                st.success("Consumption saved. Stock, the five-reading average, and estimated days have been updated.")
                st.rerun()
            except APIError as error:
                st.error(str(error))
        st.markdown("#### Order insulin")
        active_order=next((o for o in reversed(data["deliveries"]) if o["patient_id"]==pid and o["status"] not in ("Rejected","Received and Confirmed by Patient")),None)
        if active_order:
            st.info(f"Your insulin order is in the delivery process. Current status: **{active_order['status']}**.")
            order_type=active_order.get("diabetes_type") or p.get("diabetes_type", "—")
            st.caption(f"{order_type} · {int(active_order.get('quantity', 0))} units requested · Order {active_order['order_id']}")
            _render_manual_order_progress(active_order)
            if active_order["status"]=="Delivered" and st.button("Confirm I received this delivery",key="confirm_"+active_order["order_id"]):
                try:
                    post(f"/orders/{active_order['order_id']}/confirm", token)
                    st.rerun()
                except APIError as error:
                    st.error(str(error))
        if active_order is None:
            current_stock=max(0,float(p["units_available"]))
            allowed_order=max(0,int(MAX_PATIENT_STOCK-current_stock))
            if allowed_order == 0:
                st.info(f"Your insulin stock is {current_stock} units, the {MAX_PATIENT_STOCK}-unit storage limit. There is no room for another order.")
            else:
                with st.form("patient_order_form"):
                    order_units=st.number_input("Insulin units to order",min_value=1,max_value=allowed_order,
                                                value=min(allowed_order,max(1,int(round(p["daily_consumption"]*10)))),step=1)
                    place_order=st.form_submit_button("Order insulin")
                if place_order:
                    try:
                        post(f"/patients/{pid}/orders", token, {"units": order_units})
                        st.success("Your insulin order has been placed.")
                        st.rerun()
                    except APIError as error:
                        st.error(str(error))
