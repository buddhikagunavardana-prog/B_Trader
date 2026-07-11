import json
import os
from pathlib import Path

import pandas as pd


def ensure_report_dir(path: str) -> None:
    directory = Path(path).parent
    if str(directory):
        os.makedirs(directory, exist_ok=True)


def save_csv_report(report: pd.DataFrame, path: str) -> None:
    ensure_report_dir(path)
    report.to_csv(path, index=False)


def save_json_report(payload, path: str) -> None:
    ensure_report_dir(path)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=4)


def sort_report(
    report: pd.DataFrame,
    by: list[str],
    ascending: list[bool] | bool,
) -> pd.DataFrame:
    if report.empty:
        return report

    return report.sort_values(by=by, ascending=ascending)
