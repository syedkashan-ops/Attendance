from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
import math
import pandas as pd
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

SHEET_NAME = "Visits"
HEADERS = [
    "Visit ID", "Date", "Employee Code", "Employee Name", "Outlet Code", "Outlet Name",
    "IN Date/Time", "IN Latitude", "IN Longitude", "IN GPS Accuracy",
    "OUT Date/Time", "OUT Latitude", "OUT Longitude", "OUT GPS Accuracy",
    "IN-OUT GPS Distance (m)", "GPS Status", "Time Spent", "Time Spent Hours", "Status",
]


def get_client():
    info = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(credentials)


@st.cache_resource(show_spinner=False)
def get_client_cached():
    return get_client()


def get_worksheet():
    gc = get_client_cached()
    sh = gc.open_by_key(st.secrets["GOOGLE_SHEET_ID"])
    try:
        ws = sh.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_NAME, rows=2000, cols=len(HEADERS))
    values = ws.get_all_values()
    if not values:
        ws.append_row(HEADERS, value_input_option="USER_ENTERED")
    elif values[0] != HEADERS and not any(str(x).strip() for x in values[0]):
        ws.update("A1", [HEADERS], value_input_option="USER_ENTERED")
    return ws


def get_all_visits():
    ws = get_worksheet()
    records = ws.get_all_records(default_blank="")
    if not records:
        return pd.DataFrame(columns=HEADERS)
    df = pd.DataFrame(records)
    for col in HEADERS:
        if col not in df.columns:
            df[col] = ""
    return df[HEADERS]


def _today():
    return datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y-%m-%d")


def _visit_id():
    stamp = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y%m%d%H%M%S")
    return f"VIS-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def find_open_visit(employee_code):
    df = get_all_visits()
    if df.empty:
        return None
    matches = df[(df["Date"].astype(str) == _today()) &
                 (df["Employee Code"].astype(str).str.strip() == str(employee_code).strip()) &
                 (df["Status"].astype(str).str.strip() == "IN")]
    if matches.empty:
        return None
    return matches.iloc[-1].to_dict()


def create_in_visit(employee_code, employee_name, outlet_code, outlet_name, location):
    ws = get_worksheet()
    if find_open_visit(employee_code) is not None:
        raise ValueError("An open visit already exists for this employee.")
    now = datetime.now(ZoneInfo("Asia/Karachi"))
    visit_id = _visit_id()
    row = [
        visit_id, now.strftime("%Y-%m-%d"), employee_code, employee_name, outlet_code, outlet_name,
        now.strftime("%Y-%m-%d %H:%M:%S"), location["latitude"], location["longitude"], location.get("accuracy", ""),
        "", "", "", "", "", "", "", "", "IN",
    ]
    ws.append_row(row, value_input_option="USER_ENTERED", insert_data_option="INSERT_ROWS")
    return visit_id


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1 = math.radians(float(lat1)); p2 = math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1)); dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _row_number_for_visit(ws, visit_id):
    for idx, value in enumerate(ws.col_values(1), start=1):
        if str(value).strip() == str(visit_id).strip():
            return idx
    return None


def complete_out_visit(visit_id, location, tolerance_meters=100, warning_meters=200):
    ws = get_worksheet()
    row_num = _row_number_for_visit(ws, visit_id)
    if row_num is None:
        raise ValueError("Visit ID was not found.")
    row_values = ws.row_values(row_num)
    row = dict(zip(HEADERS, row_values + [""] * (len(HEADERS) - len(row_values))))
    if str(row.get("Status", "")).strip() != "IN":
        raise ValueError("This visit is already completed or invalid.")

    distance = _haversine_m(row["IN Latitude"], row["IN Longitude"], location["latitude"], location["longitude"])
    if distance <= tolerance_meters:
        gps_status = "Almost Same"
    elif distance <= warning_meters:
        gps_status = "Some Difference"
    else:
        gps_status = "Big Difference"

    in_time = datetime.strptime(str(row["IN Date/Time"]), "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Karachi"))
    out_time = datetime.now(ZoneInfo("Asia/Karachi"))
    seconds = max(0, int((out_time - in_time).total_seconds()))
    hours = seconds / 3600
    time_spent = f"{seconds//3600:02d}:{(seconds%3600)//60:02d}:{seconds%60:02d}"
    updates = [out_time.strftime("%Y-%m-%d %H:%M:%S"), location["latitude"], location["longitude"], location.get("accuracy", ""), round(distance, 1), gps_status, time_spent, round(hours, 4), "Completed"]
    ws.update(f"K{row_num}:S{row_num}", [updates], value_input_option="USER_ENTERED")
    result = row.copy()
    result.update(dict(zip(HEADERS[10:], updates)))
    return result
