from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
import math
import time
import threading
import pandas as pd
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

SHEET_NAME = "Visits"
HEADERS = [
    "Visit ID", "Date", "Employee Code", "Employee Name", "Outlet Code", "Outlet Name",
    "IN Date/Time", "IN Latitude", "IN Longitude", "IN GPS Accuracy",
    "OUT Date/Time", "OUT Latitude", "OUT Longitude", "OUT GPS Accuracy",
    "IN-OUT GPS Distance (m)", "GPS Status", "Time Spent", "Time Spent Hours", "Status",
]
INTERNAL_ROW = "__sheet_row"
REFRESH_SECONDS = 30


def get_client():
    info = dict(st.secrets["gcp_service_account"])
    private_key = str(info.get("private_key", ""))
    if "\\n" in private_key:
        private_key = private_key.replace("\\n", "\n")
    info["private_key"] = private_key.strip() + "\n"
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(credentials)


@st.cache_resource(show_spinner=False)
def get_client_cached():
    return get_client()


@st.cache_resource(show_spinner=False)
def get_worksheet_cached():
    """Open the worksheet once per Streamlit process/session lifetime."""
    gc = get_client_cached()
    sh = gc.open_by_key(st.secrets["GOOGLE_SHEET_ID"])
    try:
        ws = sh.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_NAME, rows=2000, cols=len(HEADERS))

    # IMPORTANT: only one small read on first initialization; never get_all_values().
    header = ws.row_values(1)
    if not header:
        ws.update("A1:S1", [HEADERS], value_input_option="USER_ENTERED")
    elif header != HEADERS:
        # Only repair a completely blank/missing header, never overwrite user data.
        if not any(str(x).strip() for x in header):
            ws.update("A1:S1", [HEADERS], value_input_option="USER_ENTERED")
    return ws


class VisitStore:
    """Thread-safe in-memory mirror of the Visits sheet.

    One Sheets read refreshes the whole mirror. Normal app reruns use the mirror.
    Successful IN/OUT writes update the mirror directly, avoiding a read-after-write.
    """
    def __init__(self):
        self.lock = threading.RLock()
        self.df = None
        self.last_refresh = 0.0

    def _read_sheet(self):
        ws = get_worksheet_cached()
        last_error = None
        for attempt in range(4):
            try:
                records = ws.get_all_records(default_blank="")
                rows = []
                for i, record in enumerate(records, start=2):
                    row = {col: record.get(col, "") for col in HEADERS}
                    row[INTERNAL_ROW] = i
                    rows.append(row)
                df = pd.DataFrame(rows, columns=HEADERS + [INTERNAL_ROW])
                return df
            except APIError as exc:
                last_error = exc
                if "429" not in str(exc):
                    raise
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"Google Sheets is temporarily rate-limited. Please try again shortly. {last_error}")

    def refresh_if_needed(self, force=False):
        with self.lock:
            age = time.monotonic() - self.last_refresh
            if force or self.df is None or age >= REFRESH_SECONDS:
                self.df = self._read_sheet()
                self.last_refresh = time.monotonic()
            return self.df.copy(deep=True)

    def force_refresh(self):
        return self.refresh_if_needed(force=True)

    def add_row(self, row, sheet_row):
        with self.lock:
            new_row = {col: row.get(col, "") for col in HEADERS}
            new_row[INTERNAL_ROW] = sheet_row
            if self.df is None:
                self.df = pd.DataFrame([new_row], columns=HEADERS + [INTERNAL_ROW])
            else:
                self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
            self.last_refresh = time.monotonic()

    def update_row(self, visit_id, updates):
        with self.lock:
            if self.df is None:
                return
            mask = self.df["Visit ID"].astype(str).str.strip() == str(visit_id).strip()
            for col, value in updates.items():
                if col in self.df.columns:
                    self.df.loc[mask, col] = value
            self.last_refresh = time.monotonic()


@st.cache_resource(show_spinner=False)
def get_visit_store():
    return VisitStore()


def get_all_visits(force_refresh=False):
    df = get_visit_store().refresh_if_needed(force=force_refresh)
    return df[HEADERS].copy()


def refresh_visits():
    return get_visit_store().force_refresh()[HEADERS].copy()


def _today():
    return datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y-%m-%d")


def _visit_id():
    stamp = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y%m%d%H%M%S")
    return f"VIS-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def find_open_visit(employee_code):
    df = get_visit_store().refresh_if_needed()
    if df.empty:
        return None
    matches = df[(df["Date"].astype(str) == _today()) &
                 (df["Employee Code"].astype(str).str.strip() == str(employee_code).strip()) &
                 (df["Status"].astype(str).str.strip() == "IN")]
    if matches.empty:
        return None
    return matches.iloc[-1].to_dict()


def create_in_visit(employee_code, employee_name, outlet_code, outlet_name, location):
    store = get_visit_store()
    with store.lock:
        df = store.refresh_if_needed()
        if not df.empty:
            matches = df[(df["Date"].astype(str) == _today()) &
                         (df["Employee Code"].astype(str).str.strip() == str(employee_code).strip()) &
                         (df["Status"].astype(str).str.strip() == "IN")]
            if not matches.empty:
                raise ValueError("An open visit already exists for this employee.")

        ws = get_worksheet_cached()
        now = datetime.now(ZoneInfo("Asia/Karachi"))
        visit_id = _visit_id()
        row = {
            "Visit ID": visit_id,
            "Date": now.strftime("%Y-%m-%d"),
            "Employee Code": employee_code,
            "Employee Name": employee_name,
            "Outlet Code": outlet_code,
            "Outlet Name": outlet_name,
            "IN Date/Time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "IN Latitude": location["latitude"],
            "IN Longitude": location["longitude"],
            "IN GPS Accuracy": location.get("accuracy", ""),
            "OUT Date/Time": "", "OUT Latitude": "", "OUT Longitude": "", "OUT GPS Accuracy": "",
            "IN-OUT GPS Distance (m)": "", "GPS Status": "", "Time Spent": "", "Time Spent Hours": "", "Status": "IN",
        }
        values = [row[h] for h in HEADERS]
        response = ws.append_row(
            values,
            value_input_option="USER_ENTERED",
            insert_data_option="INSERT_ROWS",
            include_values_in_response=True,
        )
        sheet_row = None
        try:
            updated_range = response.get("updates", {}).get("updatedRange", "")
            import re
            match = re.search(r"!(?:[A-Z]+)(\d+):", str(updated_range))
            if match:
                sheet_row = int(match.group(1))
        except Exception:
            sheet_row = None
        if sheet_row is None:
            sheet_row = max(2, len(df) + 2)
        store.add_row(row, sheet_row)
        return visit_id


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1 = math.radians(float(lat1)); p2 = math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1)); dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def complete_out_visit(visit_id, location, tolerance_meters=100, warning_meters=200):
    store = get_visit_store()
    df = store.refresh_if_needed()
    matches = df[df["Visit ID"].astype(str).str.strip() == str(visit_id).strip()]
    if matches.empty:
        # One forced read only if the local mirror does not know this visit.
        df = store.force_refresh()
        matches = df[df["Visit ID"].astype(str).str.strip() == str(visit_id).strip()]
    if matches.empty:
        raise ValueError("Visit ID was not found.")

    row = matches.iloc[-1].to_dict()
    if str(row.get("Status", "")).strip() != "IN":
        raise ValueError("This visit is already completed or invalid.")

    row_num = int(row[INTERNAL_ROW])
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

    updates = {
        "OUT Date/Time": out_time.strftime("%Y-%m-%d %H:%M:%S"),
        "OUT Latitude": location["latitude"],
        "OUT Longitude": location["longitude"],
        "OUT GPS Accuracy": location.get("accuracy", ""),
        "IN-OUT GPS Distance (m)": round(distance, 1),
        "GPS Status": gps_status,
        "Time Spent": time_spent,
        "Time Spent Hours": round(hours, 4),
        "Status": "Completed",
    }
    values = [updates[h] for h in HEADERS[10:]]
    ws = get_worksheet_cached()
    ws.update(f"K{row_num}:S{row_num}", [values], value_input_option="USER_ENTERED")
    store.update_row(visit_id, updates)

    row.update(updates)
    return {h: row.get(h, "") for h in HEADERS}
