from pathlib import Path
import csv
import json
import os

import gspread
from google.oauth2.service_account import Credentials


ROOT_DIR = Path(__file__).resolve().parent.parent

CSV_FILE = ROOT_DIR / "data" / "jobs.csv"
SERVICE_ACCOUNT_FILE = ROOT_DIR / "service_account.json"

SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID") or "12DHXo1gfbXLHJl6y_2v1AzLuqhfd1qFVlCPZk9XtjJ0"
WORKSHEET_NAME = "Public Jobs"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


def load_csv_rows() -> list[list[str]]:
    if not CSV_FILE.exists():
        raise FileNotFoundError(f"Missing CSV file: {CSV_FILE}")

    with CSV_FILE.open("r", encoding="utf-8", newline="") as file:
        return list(csv.reader(file))


def get_client():
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if service_account_json:
        service_account_info = json.loads(service_account_json)
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES,
        )
    else:
        credentials = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES,
        )

    return gspread.authorize(credentials)


def main():
    rows = load_csv_rows()

    if not rows:
        print("jobs.csv is empty. Nothing to publish.")
        return

    client = get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=WORKSHEET_NAME,
            rows=100,
            cols=20,
        )

    worksheet.clear()
    worksheet.update(
    values=rows,
    range_name="A1",
    value_input_option="USER_ENTERED",
    )

    worksheet.freeze(rows=1)
    worksheet.format(
        "A1:L1",
        {
            "textFormat": {"bold": True},
            "horizontalAlignment": "CENTER",
            "backgroundColor": {
                "red": 0.85,
                "green": 0.92,
                "blue": 1.0,
            },
        },
    )

    print(f"Published {len(rows) - 1} jobs to Google Sheets.")


if __name__ == "__main__":
    main()