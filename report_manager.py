import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
import pandas as pd


def dataframe_to_excel_bytes(df, report_date):
    if df is None:
        df = pd.DataFrame()

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if df.empty:
            columns = [
                "Visit ID",
                "Date",
                "Employee Code",
                "Employee Name",
                "Outlet Code",
                "Outlet Name",
                "IN Date/Time",
                "IN Latitude",
                "IN Longitude",
                "IN GPS Accuracy",
                "OUT Date/Time",
                "OUT Latitude",
                "OUT Longitude",
                "OUT GPS Accuracy",
                "IN-OUT GPS Distance (m)",
                "GPS Status",
                "Time Spent",
                "Time Spent Hours",
                "Status",
            ]
            pd.DataFrame(columns=columns).to_excel(
                writer,
                index=False,
                sheet_name="Visits",
            )
        else:
            df.to_excel(
                writer,
                index=False,
                sheet_name="Visits",
            )

        wb = writer.book
        ws = writer.sheets["Visits"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")

        for col_cells in ws.columns:
            max_len = 0
            for cell in col_cells:
                value = "" if cell.value is None else str(cell.value)
                max_len = max(max_len, len(value))
            width = min(max(max_len + 2, 12), 35)
            ws.column_dimensions[get_column_letter(
                col_cells[0].column
            )].width = width

    return output.getvalue()
