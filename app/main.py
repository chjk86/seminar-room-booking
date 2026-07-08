"""
대학원 세미나실 예약 시스템 - 백엔드 (FastAPI)

- 세미나실 1개, 로그인 없이 이름만으로 예약/취소
- 같은 시간대 중복 예약 방지
- 본인 이름이 일치해야 취소 가능
- 프론트엔드는 3초 주기로 폴링하여 다른 사람의 예약/취소를 거의 실시간으로 반영
"""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

# ----------------------------------------------------------------------------
# 설정값 (필요에 따라 자유롭게 수정하세요)
# ----------------------------------------------------------------------------
ROOM_NAME = "대학원 세미나실"
OPEN_TIME = "09:00"   # 예약 가능 시작 시각
CLOSE_TIME = "22:00"  # 예약 가능 종료 시각
SLOT_MINUTES = 30      # 시간 선택 단위(분)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "reservations.db"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="세미나실 예약 시스템")


# ----------------------------------------------------------------------------
# DB
# ----------------------------------------------------------------------------
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                purpose TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reservations_date ON reservations(date)"
        )


init_db()


# ----------------------------------------------------------------------------
# 모델
# ----------------------------------------------------------------------------
class ReservationCreate(BaseModel):
    name: str
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    purpose: Optional[str] = ""

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("이름을 입력해주세요.")
        if len(v) > 30:
            raise ValueError("이름이 너무 깁니다.")
        return v

    @field_validator("date")
    @classmethod
    def valid_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).")
        return v

    @field_validator("start_time", "end_time")
    @classmethod
    def valid_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("시간 형식이 올바르지 않습니다 (HH:MM).")
        return v


class ReservationCancel(BaseModel):
    name: str


# ----------------------------------------------------------------------------
# 헬퍼
# ----------------------------------------------------------------------------
def to_minutes(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "date": row["date"],
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "purpose": row["purpose"] or "",
        "created_at": row["created_at"],
    }


# ----------------------------------------------------------------------------
# API
# ----------------------------------------------------------------------------
@app.get("/api/config")
def get_config():
    return {
        "room_name": ROOM_NAME,
        "open_time": OPEN_TIME,
        "close_time": CLOSE_TIME,
        "slot_minutes": SLOT_MINUTES,
        "today": date.today().isoformat(),
    }


@app.get("/api/reservations")
def list_reservations(date: str):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).")

    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM reservations WHERE date = ? ORDER BY start_time",
            (date,),
        ).fetchall()
    return [row_to_dict(r) for r in rows]


@app.post("/api/reservations")
def create_reservation(payload: ReservationCreate):
    start_min = to_minutes(payload.start_time)
    end_min = to_minutes(payload.end_time)
    open_min = to_minutes(OPEN_TIME)
    close_min = to_minutes(CLOSE_TIME)

    if end_min <= start_min:
        raise HTTPException(400, "종료 시간은 시작 시간보다 늦어야 합니다.")
    if start_min < open_min or end_min > close_min:
        raise HTTPException(
            400, f"예약 가능 시간은 {OPEN_TIME} ~ {CLOSE_TIME} 입니다."
        )

    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM reservations WHERE date = ?", (payload.date,)
        ).fetchall()

        for r in existing:
            r_start = to_minutes(r["start_time"])
            r_end = to_minutes(r["end_time"])
            if start_min < r_end and end_min > r_start:
                raise HTTPException(
                    409,
                    f"이미 예약된 시간과 겹칩니다 ({r['start_time']}~{r['end_time']}, "
                    f"{r['name']}).",
                )

        cur = conn.execute(
            """
            INSERT INTO reservations (name, date, start_time, end_time, purpose, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.date,
                payload.start_time,
                payload.end_time,
                payload.purpose,
                datetime.now().isoformat(),
            ),
        )
        new_id = cur.lastrowid
        row = conn.execute(
            "SELECT * FROM reservations WHERE id = ?", (new_id,)
        ).fetchone()

    return row_to_dict(row)


@app.delete("/api/reservations/{reservation_id}")
def cancel_reservation(reservation_id: int, payload: ReservationCancel):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM reservations WHERE id = ?", (reservation_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(404, "예약을 찾을 수 없습니다.")
        if row["name"].strip() != payload.name.strip():
            raise HTTPException(403, "예약자 이름이 일치하지 않아 취소할 수 없습니다.")

        conn.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))

    return {"ok": True}


# ----------------------------------------------------------------------------
# 정적 파일 (프론트엔드)
# ----------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/manifest.json")
def manifest():
    return FileResponse(STATIC_DIR / "manifest.json")


@app.get("/sw.js")
def service_worker():
    return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")
