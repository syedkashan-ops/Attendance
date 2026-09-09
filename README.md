# Petrol Station Visit & Attendance App

Streamlit mobile web app for employee petrol-station visits.

## Architecture

Employees use Streamlit.
Live visit records are stored in Google Sheets.
Daily Excel reports are generated from Google Sheets and stored in a separate private GitHub report repository.

## Main features

- Employee Code / Name
- Outlet Code / Name
- GPS permission and location capture
- IN and OUT attendance
- IN/OUT timestamps
- IN/OUT GPS coordinates
- IN-to-OUT GPS distance
- GPS status
- Time spent
- Daily Excel reports
- Password-protected report downloads

## Secrets

The app expects:

ADMIN_PASSWORD = "..."
GOOGLE_SHEET_ID = "..."
GITHUB_TOKEN = "..."
GITHUB_REPORT_REPO = "owner/private-report-repository"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
universe_domain = "googleapis.com"
