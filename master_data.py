from io import BytesIO
import threading
import time
import pandas as pd
import streamlit as st

from sheets_handler import get_client_cached, _sheet_write

OUTLET_SHEET = "Outlets"
OUTLET_HEADERS = ["Outlet Code", "Outlet Name", "Latitude", "Longitude", "Active"]
MASTER_REFRESH_SECONDS = 120

def _clean_code(value):
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text

def _clean_active(value):
    if pd.isna(value) or str(value).strip() == "":
        return True
    return str(value).strip().lower() not in {"false", "0", "no", "inactive", "n"}

def _get_spreadsheet():
    gc = get_client_cached()
    return gc.open_by_key(st.secrets["GOOGLE_SHEET_ID"])

@st.cache_resource(show_spinner=False)
def get_master_store():
    return MasterStore()

class MasterStore:
    def __init__(self):
        self.lock = threading.RLock()
        self.outlets = None
        self.last_refresh = 0.0
        self.version = 0

    def _worksheet(self, title=OUTLET_SHEET, headers=OUTLET_HEADERS, rows=2000):
        sh = _get_spreadsheet()
        try:
            ws = sh.worksheet(title)
        except Exception:
            ws = _sheet_write(lambda: sh.add_worksheet(title=title, rows=max(rows, 100), cols=len(headers)))
        header = ws.row_values(1)
        if not header:
            _sheet_write(lambda: ws.update("A1:E1", [headers], value_input_option="USER_ENTERED"))
        return ws

    def refresh_if_needed(self, force=False):
        with self.lock:
            if force or self.outlets is None or time.monotonic() - self.last_refresh >= MASTER_REFRESH_SECONDS:
                ow = self._worksheet()
                records = ow.get_all_records(default_blank="")
                self.outlets = self._normalize_outlets(pd.DataFrame(records, columns=OUTLET_HEADERS))
                self.last_refresh = time.monotonic()
                self.version += 1
            return self.outlets.copy(deep=True)

    @staticmethod
    def _normalize_outlets(df):
        if df.empty:
            return pd.DataFrame(columns=OUTLET_HEADERS)
        x = df.copy()
        x["Outlet Code"] = x["Outlet Code"].map(_clean_code)
        x["Outlet Name"] = x["Outlet Name"].fillna("").astype(str).str.strip()
        x["Latitude"] = pd.to_numeric(x["Latitude"], errors="coerce")
        x["Longitude"] = pd.to_numeric(x["Longitude"], errors="coerce")
        x["Active"] = x["Active"].map(_clean_active)
        return x[OUTLET_HEADERS].drop_duplicates(subset=["Outlet Code"], keep="last")

    def replace_outlets(self, df):
        clean = self._normalize_outlets(df)
        self._validate_outlets(clean)
        ws = self._worksheet(rows=max(2000, len(clean) + 10))
        rows = [OUTLET_HEADERS] + clean.astype(object).where(pd.notna(clean), "").values.tolist()
        _sheet_write(lambda: ws.clear())
        _sheet_write(lambda: ws.update(f"A1:E{len(rows)}", rows, value_input_option="USER_ENTERED"))
        with self.lock:
            self.outlets = clean
            self.last_refresh = time.monotonic()
            self.version += 1
        return clean

    @staticmethod
    def _validate_outlets(df):
        errors = []
        if df["Outlet Code"].eq("").any(): errors.append("Outlet Code contains blank values.")
        if (~df["Outlet Code"].str.fullmatch(r"\d+").fillna(False)).any(): errors.append("Outlet Code must contain numbers only.")
        if df["Outlet Name"].astype(str).str.strip().eq("").any(): errors.append("Outlet Name contains blank values.")
        if df["Latitude"].isna().any() or df["Longitude"].isna().any(): errors.append("Every outlet must have valid Latitude and Longitude.")
        if ((df["Latitude"] < -90) | (df["Latitude"] > 90)).any(): errors.append("Latitude must be between -90 and 90.")
        if ((df["Longitude"] < -180) | (df["Longitude"] > 180)).any(): errors.append("Longitude must be between -180 and 180.")
        if df["Outlet Code"].duplicated().any(): errors.append("Duplicate Outlet Code found.")
        if errors: raise ValueError(" ".join(errors))

def get_master_data(force=False):
    return get_master_store().refresh_if_needed(force=force)

def lookup_outlet(code):
    outlets = get_master_data()[0] if isinstance(get_master_data(), tuple) else get_master_data()
    code = _clean_code(code)
    if outlets.empty: return None
    m = outlets[(outlets["Outlet Code"] == code) & (outlets["Active"] == True)]
    return None if m.empty else m.iloc[0].to_dict()

def master_status():
    outlets = get_master_data()
    return {
        "outlets": len(outlets),
        "active_outlets": int(outlets["Active"].sum()) if not outlets.empty else 0,
        "version": get_master_store().version,
    }

def template_excel(kind="outlets"):
    df = pd.DataFrame([{
        "Outlet Code": "1001",
        "Outlet Name": "PSO - Example II & Co.",
        "Latitude": 24.8607,
        "Longitude": 67.0011,
        "Active": True,
    }])
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Outlets")
    return bio.getvalue()
