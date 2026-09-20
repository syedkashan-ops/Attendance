# Customer Care Day — V10

V10 adds controlled Employee and Outlet Master Data while preserving the V9 employee visit workflow, GPS capture, PWA styling, admin reports, analytics, caching, throttled Google Sheets writes, and batched GitHub reporting.

## Google Sheet worksheets

The existing `Visits` worksheet remains the transaction database and is not changed.

V10 automatically creates two additional worksheets:

### Employees
Required columns:
- Employee Code
- Employee Name
- Active

### Outlets
Required columns:
- Outlet Code
- Outlet Name
- Latitude
- Longitude
- Active

Outlet Latitude/Longitude are decimal GPS coordinates. Latitude must be -90 to 90 and longitude -180 to 180.

## Employee workflow

Employees enter only Employee Code and Outlet Code. The application retrieves the official active Employee Name and Outlet Name from the master sheets. Unknown or inactive codes are rejected.

The selected outlet's master GPS coordinates are retained with the session and displayed before the GPS IN step. Existing IN/OUT GPS coordinates and IN-to-OUT distance calculations are unchanged.

## Admin master upload

Admin / Reports contains Employee & Outlet Master Data. Download the templates, populate them, and upload them to replace the corresponding master worksheet.

Do not upload the Google service-account JSON or private keys to GitHub.

## Deployment

Replace the existing Attendance repository files with this `attendance` folder. Keep the existing Streamlit Secrets unchanged.
