# Petrol Station Visit & Attendance

Mobile-first Streamlit attendance app for employee IN/OUT visits.

## Current GPS implementation

This version uses Streamlit Components V2 and the browser's native Geolocation API. The previous `streamlit-geolocation` package has been removed.

The browser requests a fresh high-accuracy position with:

- `enableHighAccuracy: true`
- `maximumAge: 0`
- `timeout: 20 seconds`

The app stores latitude, longitude and browser-reported accuracy for IN and OUT.

## Deployment

Use Python 3.12 on Streamlit Community Cloud if selecting the Python version during deployment. The current requirements pin Streamlit 1.63.0 because Components V2 is used by the GPS implementation.

Required Streamlit Secrets remain the same:

```toml
ADMIN_PASSWORD = "YOUR_ADMIN_PASSWORD"
GOOGLE_SHEET_ID = "YOUR_GOOGLE_SHEET_ID"
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"
GITHUB_REPORT_REPO = "YOUR_GITHUB_USERNAME/petrol-station-visit-reports"

[gcp_service_account]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key_id = "YOUR_PRIVATE_KEY_ID"
private_key = """-----BEGIN PRIVATE KEY-----
YOUR NEW PRIVATE KEY CONTENT
-----END PRIVATE KEY-----"""
client_email = "YOUR_SERVICE_ACCOUNT_EMAIL"
client_id = "YOUR_CLIENT_ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "YOUR_CLIENT_X509_CERT_URL"
universe_domain = "googleapis.com"
```

Do not commit Streamlit Secrets or Google service-account JSON files to GitHub.
