# Petrol Station Visit & Attendance — Version 5

This version keeps the V4 native browser GPS implementation and fixes the Google Sheets 429 read-quota problem by using a thread-safe shared in-memory mirror of the Visits sheet.

## Main V5 changes
- Google Sheets is normally read once every 30 seconds, not on every Streamlit rerun.
- Employee open-visit status is kept in Streamlit session state.
- Successful IN/OUT writes update the shared mirror without an immediate read-back.
- IN append uses the Google Sheets append response to obtain the actual row number when available.
- Temporary Google Sheets HTTP 429 errors use exponential backoff.
- Admin report refresh explicitly performs a fresh Google Sheets read.
- Native browser GPS from V4 is retained.

## Deploy
1. Replace the files in your existing GitHub app repository with the files in this package.
2. Do not change your existing Streamlit Secrets if they are already correct.
3. Streamlit Cloud should redeploy automatically after the GitHub commit.
4. Test one employee IN and OUT from a mobile phone.

## Important
The Google Sheet remains the live database. The in-memory cache is only a performance layer; it is not a replacement database.

Google Sheets API access is shared across app users, so reducing repeated reads is important when many employees use the app. Streamlit documents that `st.cache_resource` resources can be shared across users/sessions and must be thread-safe; V5 therefore protects the shared visit mirror with a lock.
