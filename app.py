from datetime import datetime
from zoneinfo import ZoneInfo
import os
import pandas as pd
import streamlit as st

from sheets_handler import (
    get_all_visits,
    find_open_visit,
    create_in_visit,
    complete_out_visit,
)
from report_manager import dataframe_to_excel_bytes
from github_reports import upload_or_update_report, list_reports, download_report

APP_TITLE = "Petrol Station Visit & Attendance"
GPS_TOLERANCE_METERS = 100
GPS_WARNING_METERS = 200
MAX_ACCEPTABLE_GPS_ACCURACY_METERS = 1000

st.set_page_config(page_title=APP_TITLE, page_icon="⛽", layout="centered")

for key, default in {
    "employee_code": "",
    "employee_name": "",
    "outlet_code": "",
    "outlet_name": "",
    "in_location": None,
    "out_location": None,
    "admin_logged_in": False,
    "last_message": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def now_local():
    return datetime.now(ZoneInfo("Asia/Karachi"))


def get_location():
    from streamlit_geolocation import streamlit_geolocation

    st.caption("Turn ON phone Location/GPS and allow location permission.")

    loc = streamlit_geolocation()

    st.write("GPS response:", loc)

    if loc and loc.get("latitude") is not None:
        result = {
            "latitude": float(loc["latitude"]),
            "longitude": float(loc["longitude"]),
            "accuracy": (
                float(loc["accuracy"])
                if loc.get("accuracy") is not None
                else None
            ),
        }

        st.success("GPS location captured.")
        st.write(f"Latitude: `{result['latitude']:.6f}`")
        st.write(f"Longitude: `{result['longitude']:.6f}`")

        if result["accuracy"] is not None:
            st.write(
                f"Accuracy: approximately `{result['accuracy']:.0f} metres`"
            )

        return result

    if loc and loc.get("error"):
        st.error(f"GPS Error: {loc['error']}")

    else:
        st.warning(
            "GPS location has not been returned yet. "
            "Please tap the GPS icon again and wait a few seconds."
        )

    return None


def location_ok(location):
    if not location:
        return False, "Please capture your current GPS location."
    lat = location.get("latitude")
    lon = location.get("longitude")
    accuracy = location.get("accuracy")
    if lat is None or lon is None:
        return False, "GPS coordinates were not received."
    if accuracy is not None and float(accuracy) > MAX_ACCEPTABLE_GPS_ACCURACY_METERS:
        return False, f"GPS accuracy is too low ({float(accuracy):.0f} m). Please move to an open area and try again."
    return True, ""


def sync_today_report():
    today_str = now_local().strftime("%Y-%m-%d")
    df = get_all_visits()
    if not df.empty:
        df["Date"] = df["Date"].astype(str)
        day_df = df[df["Date"] == today_str].copy()
    else:
        day_df = pd.DataFrame()
    excel_bytes = dataframe_to_excel_bytes(day_df, today_str)
    path = f"data/visits/Visits_{today_str}.xlsx"
    upload_or_update_report(path, excel_bytes, f"Sync daily report {today_str}")
    return path


with st.sidebar:
    st.title("⛽ Visit System")
    menu = st.radio("Menu", ["Employee Visit", "Admin / Reports"])
    st.divider()
    st.caption("Live records are stored in Google Sheets. Daily Excel reports are archived in GitHub.")


if menu == "Employee Visit":
    st.title("⛽ Petrol Station Visit")
    st.caption("Employee IN / OUT Attendance")

    if st.session_state["last_message"]:
        st.info(st.session_state["last_message"])

    st.subheader("Employee & Outlet Details")
    with st.form("visit_details_form"):
        employee_code_input = st.text_input("Employee Code", value=st.session_state["employee_code"], max_chars=50)
        employee_name_input = st.text_input("Employee Name", value=st.session_state["employee_name"], max_chars=100)
        outlet_code_input = st.text_input("Outlet Code", value=st.session_state["outlet_code"], max_chars=50)
        outlet_name_input = st.text_input("Outlet Name", value=st.session_state["outlet_name"], max_chars=150)
        details_submitted = st.form_submit_button("Continue", type="primary", use_container_width=True)

    if details_submitted:
        employee_code_input = employee_code_input.strip()
        employee_name_input = employee_name_input.strip()
        outlet_code_input = outlet_code_input.strip()
        outlet_name_input = outlet_name_input.strip()
        if not all([employee_code_input, employee_name_input, outlet_code_input, outlet_name_input]):
            st.error("Please enter Employee Code, Employee Name, Outlet Code and Outlet Name.")
        else:
            st.session_state["employee_code"] = employee_code_input
            st.session_state["employee_name"] = employee_name_input
            st.session_state["outlet_code"] = outlet_code_input
            st.session_state["outlet_name"] = outlet_name_input
            st.session_state["in_location"] = None
            st.session_state["out_location"] = None
            st.session_state["last_message"] = "Details accepted. Checking today's attendance..."
            st.rerun()

    employee_code = st.session_state["employee_code"].strip()
    employee_name = st.session_state["employee_name"].strip()
    outlet_code = st.session_state["outlet_code"].strip()
    outlet_name = st.session_state["outlet_name"].strip()

    if not employee_code or not employee_name or not outlet_code or not outlet_name:
        st.info("Enter the employee and outlet details, then press Continue.")
        st.stop()

    # Google Sheets is contacted only after the employee presses Continue.
    try:
        open_visit = find_open_visit(employee_code)
    except Exception as exc:
        st.error(f"Unable to check current attendance: {exc}")
        st.stop()

    st.divider()
    st.caption(f"Employee: {employee_name} | Outlet: {outlet_name} ({outlet_code})")

    if open_visit is None:
        st.subheader("Step 1 — Capture GPS for IN")
        if st.button("📍 Get Current GPS for IN", use_container_width=True):
    loc = get_location()

    if loc and loc.get("latitude") is not None:
        st.session_state["in_location"] = loc
        st.rerun()
    else:
        st.warning(
            "GPS location is not available yet. "
            "Please wait 5–10 seconds and tap the GPS button again."
        )

if st.session_state["in_location"]:
    st.success("IN GPS is ready.")
    st.subheader("Step 2 — Mark IN")

if st.button("🟢 MARK IN", type="primary", use_container_width=True):
        ok, msg = location_ok(st.session_state["in_location"])

        if not ok:
            st.error(msg)
                else:
                    try:
                        existing = find_open_visit(employee_code)
                        if existing is not None:
                            st.warning("This employee already has an open IN visit today. Please refresh the page.")
                        else:
                            visit_id = create_in_visit(employee_code, employee_name, outlet_code, outlet_name, st.session_state["in_location"])
                            st.session_state["in_location"] = None
                            st.session_state["last_message"] = f"IN recorded successfully. Visit ID: {visit_id}"
                            try:
                                sync_today_report()
                            except Exception as sync_exc:
                                st.warning(f"IN was saved, but the GitHub Excel could not be synced yet: {sync_exc}")
                            st.success(f"✅ IN recorded. Visit ID: {visit_id}")
                            st.rerun()
                    except Exception as exc:
                        st.error("IN could not be recorded.")
                        st.exception(exc)
    else:
        st.success("🟢 This employee currently has an open visit.")
        st.write(f"**Visit ID:** {open_visit['Visit ID']}")
        st.write(f"**Employee:** {open_visit['Employee Name']}")
        st.write(f"**Outlet:** {open_visit['Outlet Name']}")
        st.write(f"**IN Time:** {open_visit['IN Date/Time']}")

        st.divider()
        st.subheader("Step 1 — Capture GPS for OUT")
        if st.button("📍 Get Current GPS for OUT", use_container_width=True):
            loc = get_location()
            if loc:
                st.session_state["out_location"] = loc
                st.rerun()

        if st.session_state["out_location"]:
            st.success("OUT GPS is ready.")
            if st.button("🔴 MARK OUT", type="primary", use_container_width=True):
                ok, msg = location_ok(st.session_state["out_location"])
                if not ok:
                    st.error(msg)
                else:
                    try:
                        if (employee_name.lower() != str(open_visit["Employee Name"]).strip().lower()
                                or outlet_code != str(open_visit["Outlet Code"]).strip()
                                or outlet_name.lower() != str(open_visit["Outlet Name"]).strip().lower()):
                            raise ValueError("Employee/Outlet details do not match the open IN visit. Please enter exactly the same details used for IN.")

                        result = complete_out_visit(open_visit["Visit ID"], st.session_state["out_location"], GPS_TOLERANCE_METERS, GPS_WARNING_METERS)
                        try:
                            sync_today_report()
                        except Exception as sync_exc:
                            st.warning(f"Visit was saved, but the GitHub daily Excel could not be synced yet: {sync_exc}")

                        st.success("✅ OUT recorded successfully.")
                        st.subheader("Visit Summary")
                        st.write(f"**Visit ID:** {result['Visit ID']}")
                        st.write(f"**IN:** {result['IN Date/Time']}")
                        st.write(f"**OUT:** {result['OUT Date/Time']}")
                        st.write(f"**Time Spent:** {result['Time Spent']} ({result['Time Spent Hours']:.2f} hours)")
                        st.write(f"**IN → OUT GPS Distance:** {result['IN-OUT GPS Distance (m)']:.1f} m")
                        status = result["GPS Status"]
                        if status == "Almost Same":
                            st.success("✅ GPS Status: Almost Same")
                        elif status == "Some Difference":
                            st.warning("⚠️ GPS Status: Some Difference")
                        else:
                            st.error("🔴 GPS Status: Big Difference")
                        st.session_state["out_location"] = None
                        st.session_state["in_location"] = None
                        st.session_state["last_message"] = "Visit completed. You can close the app."
                    except Exception as exc:
                        st.error("OUT could not be recorded.")
                        st.exception(exc)

else:
    st.title("🔐 Admin / Reports")
    if not st.session_state["admin_logged_in"]:
        password = st.text_input("Admin Password", type="password")
        if st.button("Login", type="primary", use_container_width=True):
            if password == st.secrets["ADMIN_PASSWORD"]:
                st.session_state["admin_logged_in"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")

    if st.session_state["admin_logged_in"]:
        st.success("Admin access granted.")
        try:
            all_visits = get_all_visits()
            if all_visits.empty:
                st.info("No visits have been recorded yet.")
            else:
                all_visits["Date"] = all_visits["Date"].astype(str)
                all_visits["Status"] = all_visits["Status"].astype(str)
                st.metric("Total Records", len(all_visits))
                st.metric("Completed Visits", int((all_visits["Status"] == "Completed").sum()))
                st.metric("Pending IN", int((all_visits["Status"] == "IN").sum()))
        except Exception as exc:
            st.error(f"Could not read Google Sheet: {exc}")

        st.divider()
        st.subheader("Daily Excel Reports")
        try:
            reports = list_reports()
            if not reports:
                st.info("No Excel reports have been synced yet.")
            else:
                labels = [os.path.basename(x) for x in reports]
                selected_label = st.selectbox("Select report", labels)
                selected_path = reports[labels.index(selected_label)]
                if st.button("Refresh Selected Report from Google Sheet", use_container_width=True):
                    selected_date = selected_label.replace("Visits_", "").replace(".xlsx", "")
                    df = get_all_visits()
                    if not df.empty:
                        df["Date"] = df["Date"].astype(str)
                        day_df = df[df["Date"] == selected_date].copy()
                    else:
                        day_df = pd.DataFrame()
                    upload_or_update_report(selected_path, dataframe_to_excel_bytes(day_df, selected_date), f"Refresh report {selected_date}")
                    st.success("Report refreshed in GitHub.")
                    st.rerun()
                report_bytes = download_report(selected_path)
                st.download_button("⬇️ Download Excel", data=report_bytes, file_name=selected_label,
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
        except Exception as exc:
            st.error(f"Could not load GitHub reports: {exc}")
