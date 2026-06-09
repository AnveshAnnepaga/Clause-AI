
from pathlib import Path
import pandas as pd
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
HISTORY_FILE = BASE_DIR / "analysis_history.xlsx"

def _ensure_file():
    if not HISTORY_FILE.exists():
        df = pd.DataFrame(columns=[
            "timestamp",
            "user_email",
            "filename",
            "question",
            "risk_level"
        ])
        df.to_excel(HISTORY_FILE, index=False)


def save_history(user_email, filename, question, risk):
    _ensure_file()

    df = pd.read_excel(HISTORY_FILE)

    new_row = {
        "timestamp": datetime.utcnow(),
        "user_email": user_email,
        "filename": filename,
        "question": question,
        "risk_level": risk
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(HISTORY_FILE, index=False)


def load_history(user_email):
    _ensure_file()

    df = pd.read_excel(HISTORY_FILE)
    return df[df["user_email"] == user_email].sort_values("timestamp", ascending=False)