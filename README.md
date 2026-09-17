# Customer Care Day — V9

V9 is a performance-focused upgrade of the V8 Customer Care Day Streamlit application for 1,100+ employee usage.

## V9 performance changes

- Keeps Google Sheets as the live Visits database.
- Keeps the existing employee IN/OUT workflow, GPS capture, validation, PWA-style mobile presentation, Admin/Reports, daily Excel reports, and private GitHub archive.
- Increases the shared Visits mirror refresh interval to 60 seconds to reduce unnecessary Google Sheets reads during normal Streamlit reruns.
- Adds an in-process Visits-store version counter so analytics caches can be invalidated whenever the live mirror is refreshed or an IN/OUT update changes it.
- Caches management analytics calculations for repeated Admin UI reruns (120 seconds, bounded cache).
- Caches generated Management Analytics Excel workbooks for repeated downloads/reruns (120 seconds, bounded cache).
- Caches the GitHub daily-report directory listing for normal Admin reruns (120 seconds).
- Retains the V6/V7 Google Sheets write throttle and transient-error retry logic.
- Retains the V6/V7 five-minute activity-triggered GitHub report batching.

## Deployment

Replace the existing files in the same Streamlit/GitHub application repository with this package. Keep the existing Streamlit Secrets, Google Sheet, service account, and GitHub report repository unchanged.

No new database or Google Sheet is required.
