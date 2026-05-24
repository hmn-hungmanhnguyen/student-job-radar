from pathlib import Path
import csv
import json
import os
import re

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


HYPERLINK_RE = re.compile(
    r'^=HYPERLINK\("(?P<url>(?:[^"]|"")*)","(?P<label>(?:[^"]|"")*)"\)$'
)


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


def col_to_letter(index: int) -> str:
    """Convert zero-based column index to Google Sheets column letter."""
    result = ""
    index += 1

    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result

    return result


def parse_hyperlink_formula(value: str):
    """Parse =HYPERLINK("url","label") into (label, url)."""
    match = HYPERLINK_RE.match(value.strip())

    if not match:
        return None

    url = match.group("url").replace('""', '"')
    label = match.group("label").replace('""', '"')

    return label, url


def extract_native_links(rows: list[list[str]]) -> list[tuple[int, int, str, str]]:
    """
    Replace HYPERLINK formulas with plain display text and remember
    where native Google Sheets links should be applied.

    Indexes are zero-based.
    """
    native_links = []

    for row_index, row in enumerate(rows):
        if row_index == 0:
            continue

        for col_index, value in enumerate(row):
            parsed = parse_hyperlink_formula(value)

            if parsed is None:
                continue

            label, url = parsed
            rows[row_index][col_index] = label
            native_links.append((row_index, col_index, label, url))

    return native_links


def make_native_link_requests(
    sheet_id: int,
    native_links: list[tuple[int, int, str, str]],
) -> list[dict]:
    requests = []

    for row_index, col_index, label, url in native_links:
        requests.append(
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_index,
                        "endRowIndex": row_index + 1,
                        "startColumnIndex": col_index,
                        "endColumnIndex": col_index + 1,
                    },
                    "rows": [
                        {
                            "values": [
                                {
                                    "userEnteredValue": {
                                        "stringValue": label,
                                    },
                                    "textFormatRuns": [
                                        {
                                            "startIndex": 0,
                                            "format": {
                                                "link": {
                                                    "uri": url,
                                                },
                                                "foregroundColor": {
                                                    "red": 0.0,
                                                    "green": 0.25,
                                                    "blue": 0.75,
                                                },
                                                "underline": True,
                                            },
                                        }
                                    ],
                                }
                            ]
                        }
                    ],
                    "fields": "userEnteredValue,textFormatRuns",
                }
            }
        )

    return requests


def make_dimension_request(sheet_id: int, dimension: str, start: int, end: int, pixel_size: int):
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": dimension,
                "startIndex": start,
                "endIndex": end,
            },
            "properties": {
                "pixelSize": pixel_size,
            },
            "fields": "pixelSize",
        }
    }


def hide_column_request(sheet_id: int, start: int, end: int):
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": start,
                "endIndex": end,
            },
            "properties": {
                "hiddenByUser": True,
            },
            "fields": "hiddenByUser",
        }
    }


def apply_sheet_formatting(spreadsheet, worksheet, rows: list[list[str]]) -> None:
    if not rows:
        return

    sheet_id = worksheet.id
    row_count = len(rows)
    col_count = len(rows[0])
    last_col = col_to_letter(col_count - 1)

    worksheet.freeze(rows=1)

    worksheet.format(
        f"A1:{last_col}{row_count}",
        {
            "verticalAlignment": "MIDDLE",
            "textFormat": {
                "fontSize": 10,
            },
        },
    )

    worksheet.format(
        f"A1:{last_col}1",
        {
            "backgroundColor": {
                "red": 0.20,
                "green": 0.48,
                "blue": 0.85,
            },
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
            "textFormat": {
                "bold": True,
                "fontSize": 10,
                "foregroundColor": {
                    "red": 1.0,
                    "green": 1.0,
                    "blue": 1.0,
                },
            },
        },
    )

    worksheet.format(
        "B:B",
        {
            "horizontalAlignment": "LEFT",
            "verticalAlignment": "MIDDLE",
            "wrapStrategy": "WRAP",
        },
    )

    worksheet.format(
        "K:L",
        {
            "horizontalAlignment": "LEFT",
            "verticalAlignment": "MIDDLE",
            "wrapStrategy": "WRAP",
        },
    )

    worksheet.format(
        "C:J",
        {
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
            "wrapStrategy": "CLIP",
        },
    )

    for row_number in range(2, row_count + 1):
        if row_number % 2 == 0:
            color = {"red": 1.0, "green": 1.0, "blue": 1.0}
        else:
            color = {"red": 0.90, "green": 0.94, "blue": 1.0}

        worksheet.format(
            f"A{row_number}:{last_col}{row_number}",
            {
                "backgroundColor": color,
                "verticalAlignment": "MIDDLE",
            },
        )

    headers = rows[0]

    if "Status" in headers:
        status_index = headers.index("Status")
        status_col = col_to_letter(status_index)

        status_colors = {
            "Open": {
                "backgroundColor": {"red": 0.75, "green": 0.95, "blue": 0.75},
                "textFormat": {"bold": True},
            },
            "Closing soon": {
                "backgroundColor": {"red": 1.0, "green": 0.88, "blue": 0.55},
                "textFormat": {"bold": True},
            },
            "Deadline today": {
                "backgroundColor": {"red": 1.0, "green": 0.55, "blue": 0.55},
                "textFormat": {"bold": True},
            },
            "Expired": {
                "backgroundColor": {"red": 0.80, "green": 0.80, "blue": 0.80},
                "textFormat": {"bold": True},
            },
            "No deadline found": {
                "backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.65},
                "textFormat": {"bold": True},
            },
        }

        for row_number, row in enumerate(rows[1:], start=2):
            status = row[status_index] if status_index < len(row) else ""
            formatting = status_colors.get(status)

            if formatting:
                worksheet.format(
                    f"{status_col}{row_number}:{status_col}{row_number}",
                    {
                        **formatting,
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                    },
                )

    requests = [
        hide_column_request(sheet_id, 0, 1),

        make_dimension_request(sheet_id, "COLUMNS", 1, 2, 520),   # Title
        make_dimension_request(sheet_id, "COLUMNS", 2, 3, 70),    # Type
        make_dimension_request(sheet_id, "COLUMNS", 3, 4, 95),    # Deadline
        make_dimension_request(sheet_id, "COLUMNS", 4, 5, 80),    # Days Left
        make_dimension_request(sheet_id, "COLUMNS", 5, 6, 125),   # Status
        make_dimension_request(sheet_id, "COLUMNS", 6, 7, 220),   # Contact
        make_dimension_request(sheet_id, "COLUMNS", 7, 8, 180),   # Published
        make_dimension_request(sheet_id, "COLUMNS", 8, 9, 130),   # Source Page
        make_dimension_request(sheet_id, "COLUMNS", 9, 10, 90),   # PDF
        make_dimension_request(sheet_id, "COLUMNS", 10, 11, 270), # Note
        make_dimension_request(sheet_id, "COLUMNS", 11, 12, 360), # Summary

        make_dimension_request(sheet_id, "ROWS", 0, 1, 32),
    ]

    if row_count > 1:
        requests.append(
            make_dimension_request(sheet_id, "ROWS", 1, row_count, 78)
        )

    spreadsheet.batch_update({"requests": requests})


def main():
    rows = load_csv_rows()
    native_links = extract_native_links(rows)

    if not rows:
        print("jobs.csv is empty. Nothing to publish.")
        return

    print(f"Loaded {len(rows) - 1} jobs from {CSV_FILE}")
    print("First job title:", rows[1][1] if len(rows) > 1 else "No job rows")
    print("Publishing to spreadsheet:", SPREADSHEET_ID)

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

    worksheet.batch_clear(["A1:L200"])

    worksheet.resize(
        rows=max(len(rows) + 20, 100),
        cols=max(len(rows[0]), 12),
    )

    worksheet.update(
        values=rows,
        range_name="A1",
        value_input_option="RAW",
    )

    apply_sheet_formatting(spreadsheet, worksheet, rows)

    link_requests = make_native_link_requests(worksheet.id, native_links)

    if link_requests:
        spreadsheet.batch_update({"requests": link_requests})

    print(f"Published {len(rows) - 1} jobs to Google Sheets.")


if __name__ == "__main__":
    main()