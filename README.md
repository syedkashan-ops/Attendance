# Customer Care Day — Version 5 Theme

This replacement package keeps the working V5 GPS and Google Sheets quota optimizations and applies the supplied PSO “WE CARE. YOU DRIVE.” campaign theme.

## Included
- Customer Care Day branding throughout the employee and admin screens.
- Supplied campaign artwork used as the app hero/header image.
- Deep PSO blue, green and yellow visual theme.
- White rounded cards and green action buttons.
- Four-step IN/OUT progress indicator.
- The text “Your visit helps us serve you better” has been removed.
- Working native browser GPS implementation retained.
- Automatic scrolling flow retained.
- Completed visit summary retained.
- Google Sheets read-quota optimization retained.

## Deploy
1. Extract this ZIP.
2. Replace the files in the existing GitHub Streamlit app repository, including the `assets` folder.
3. Keep the existing Streamlit Secrets unchanged.
4. Commit/push the changes and wait for Streamlit Community Cloud to redeploy.
5. Test Employee Visit on mobile.

Do not create a new Google Sheet.

## Version 5 — Customer Care Day PWA-style mobile experience

Live app: https://csdattendance.streamlit.app/

The employee form now requires all four fields and validates them as follows:
- Employee Code: numbers only
- Employee Name: alphabets and spaces only
- Outlet Code: numbers only
- Outlet Name: alphabets, numbers and spaces

The app also adds mobile/PWA-style metadata and the Customer Care Day icon so supported Android browsers can offer an app-like home-screen shortcut, while iPhone users can use Safari's Add to Home Screen feature.

### Employee installation

**Android (Chrome):** open https://csdattendance.streamlit.app/ and use Chrome's menu → **Add to Home screen** or **Install app** when offered. Name: **Customer Care Day**.

**iPhone (Safari):** open https://csdattendance.streamlit.app/ → Share → **Add to Home Screen** → Add.

The application remains online and requires internet access. GPS/location permission must remain enabled.
