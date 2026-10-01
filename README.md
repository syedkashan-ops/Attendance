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

## V10.1 Production Performance Edition
- Employee IN/OUT no longer generates Excel files or calls GitHub.
- GitHub daily report sync is admin-triggered from Admin / Reports.
- Outlet Master is cached for 30 minutes and uses an in-memory code index.
- Visits mirror refresh is reduced to once per 15 minutes per running process; successful local IN/OUT writes update the shared mirror immediately.
- Open-visit checks use an in-memory employee index instead of repeated Pandas filtering.
- Reporting/GitHub modules load only after admin authentication.
- PWA icon/manifest payload is cached instead of rebuilt on every rerun.
