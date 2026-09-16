# Customer Care Day — V7

V7 is a reliability and administration upgrade for the Customer Care Day attendance app, designed for 1,100+ employees while preserving the existing employee workflow.

## Architecture
Phone → Streamlit → Google Sheets (live) → Daily Excel → Private GitHub archive

## V7 improvements
- Existing Google Sheets write throttle and transient-error retry retained.
- Shared in-process visit mirror reduces unnecessary reads.
- Duplicate open-IN protection retained.
- Duplicate OUT protection retained by visit status locking.
- Admin dashboard with date-based KPIs.
- Admin exception review for Big GPS Difference, very short/long visits, and missing GPS accuracy.
- Downloadable exception list for management review.
- Admin logout button.
- Manual GitHub report refresh updates the sync gate to avoid immediate duplicate syncing.
- Existing GPS, validation, PWA-style UI, auto-scroll, reports, and branding are preserved.

## Deployment
Replace the contents of the existing `attendance` app repository with this folder. Keep the existing Streamlit Secrets, Google Sheet, service account, and report repository unchanged.

Do not upload Google service-account JSON or private keys to GitHub.
