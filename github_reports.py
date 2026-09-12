import base64
import time
import requests
import streamlit as st


API_ROOT = "https://api.github.com"


def _headers():
    return {
        "Authorization": f"Bearer {st.secrets['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo():
    return st.secrets["GITHUB_REPORT_REPO"]


def _url(path):
    return f"{API_ROOT}/repos/{_repo()}/contents/{path}"


def _get(path):
    response = requests.get(
        _url(path),
        headers=_headers(),
        timeout=30,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def report_exists(path):
    return _get(path) is not None


def upload_or_update_report(path, file_bytes, commit_message, retries=4):
    encoded = base64.b64encode(file_bytes).decode("utf-8")

    for attempt in range(retries):
        current = _get(path)
        payload = {
            "message": commit_message,
            "content": encoded,
        }

        if current and current.get("sha"):
            payload["sha"] = current["sha"]

        response = requests.put(
            _url(path),
            headers=_headers(),
            json=payload,
            timeout=60,
        )

        if response.ok:
            return response.json()

        # SHA conflict / concurrent update. Refresh and retry.
        if response.status_code in (409, 422):
            time.sleep(1.5 * (attempt + 1))
            continue

        response.raise_for_status()

    raise RuntimeError(
        "GitHub report update failed after multiple retries."
    )


def list_reports():
    folder = "data/visits"
    data = _get(folder)
    if not data:
        return []

    return sorted(
        [
            item["path"]
            for item in data
            if item.get("type") == "file"
            and item.get("name", "").lower().endswith(".xlsx")
        ],
        reverse=True,
    )


def download_report(path):
    data = _get(path)
    if not data:
        raise FileNotFoundError(path)

    return base64.b64decode(data["content"])
