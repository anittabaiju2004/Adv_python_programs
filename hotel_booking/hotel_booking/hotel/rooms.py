"""Room Management: rooms, categories, tariffs, availability search and
housekeeping status."""
from __future__ import annotations

import re
from collections import Counter
from datetime import date

from .auth import log_activity
from .database import JSONDatabase
from .utils import (MAX_ADVANCE_DAYS, MAX_NIGHTS, ROOM_CATEGORIES, HotelError, NotFoundError, ValidationError,
                    now_str, parse_date, validate_amount, validate_choice, validate_int, validate_text)

STATUSES = ["AVAILABLE", "OCCUPIED", "CLEANING", "MAINTENANCE"]
ACTIVE_BOOKING = ("CONFIRMED", "CHECKED_IN")


def validate_stay(check_in, check_out, allow_past: bool = False) -> tuple[date, date]:
    ci, co = parse_date(check_in, "Check-in date"), parse_date(check_out, "Check-out date")
    if co <= ci:
        raise ValidationError("Check-out must be after check-in.")
    if (co - ci).days > MAX_NIGHTS:
        raise ValidationError(f"A booking can be at most {MAX_NIGHTS} nights.")
    if not allow_past and ci < date.today():
        raise ValidationError("Check-in date cannot be in the past.")
    if (ci - date.today()).days > MAX_ADVANCE_DAYS:
        raise ValidationError(f"Bookings open only {MAX_ADVANCE_DAYS} days ahead.")
    return ci, co


class RoomManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor

    # ---------------------------------------------------------------- crud
    def add(self, room_no: str, category: str, floor=None, rate=None, notes: str = "") -> dict:
        room_no = str(room_no or "").strip().upper()
        if not re.fullmatch(r"[0-9]{1,2}[0-9]{2}[A-Z]?", room_no):
            raise ValidationError("Room number must look like 101, 1204 or 305A.")
        if self.db.find_one("rooms", room_no=room_no):
            raise ValidationError(f"Room {room_no} already exists.")
        category = validate_choice(category, ROOM_CATEGORIES, "category")
        floor = validate_int(floor if floor not in (None, "") else int(room_no[:-2] if room_no[-1].isdigit()
                                                                       else room_no[:-3]), "Floor", 0, 99)
        room = {"room_no": room_no, "category": category, "floor": floor,
                "rate": validate_amount(rate, "Tariff", 500, 1_00_000) if rate not in (None, "") else None,
                "status": "AVAILABLE", "notes": validate_text(notes, "Notes", 120), "created_at": now_str()}
        self.db.insert("rooms", room)
        log_activity(self.db, self.actor, "ROOM_ADDED", f"{room_no} {category}")
        return room

    def get(self, room_no: str) -> dict:
        r = self.db.find_one("rooms", room_no=str(room_no or "").strip().upper())
        if not r:
            raise NotFoundError(f"Room {room_no} not found.")
        return r

    def list(self, category: str | None = None, status: str | None = None) -> list[dict]:
        rooms = self.db.all("rooms")
        if category:
            category = validate_choice(category, ROOM_CATEGORIES, "category")
            rooms = [r for r in rooms if r["category"] == category]
        if status:
            rooms = [r for r in rooms if r["status"] == status.upper()]
        return sorted(rooms, key=lambda r: (r["floor"], r["room_no"]))

    @staticmethod
    def tariff(room: dict) -> float:
        return room["rate"] if room.get("rate") else ROOM_CATEGORIES[room["category"]]["rate"]

    @staticmethod
    def capacity(room: dict) -> int:
        return ROOM_CATEGORIES[room["category"]]["capacity"]

    def update(self, room_no: str, category: str | None = None, rate=None, notes: str | None = None) -> dict:
        room = self.get(room_no)
        changes = {}
        if category:
            changes["category"] = validate_choice(category, ROOM_CATEGORIES, "category")
        if rate is not None:
            changes["rate"] = None if rate == "" else validate_amount(rate, "Tariff", 500, 1_00_000)
        if notes is not None:
            changes["notes"] = validate_text(notes, "Notes", 120)
        if not changes:
            raise ValidationError("Nothing to update.")
        log_activity(self.db, self.actor, "ROOM_UPDATED", f"{room['room_no']}: {changes}")
        return self.db.update("rooms", "room_no", room["room_no"], changes)

    def delete(self, room_no: str) -> None:
        room = self.get(room_no)
        if any(b["status"] in ACTIVE_BOOKING for b in self.db.find("bookings", room_no=room["room_no"])):
            raise HotelError(f"Room {room['room_no']} has current or upcoming bookings.")
        self.db.delete("rooms", "room_no", room["room_no"])
        log_activity(self.db, self.actor, "ROOM_DELETED", room["room_no"])

    # ---------------------------------------------------------- housekeeping
    def set_status(self, room_no: str, status: str) -> dict:
        room = self.get(room_no)
        status = validate_choice(status, STATUSES, "status")
        if status == "OCCUPIED":
            raise HotelError("Rooms become OCCUPIED only through check-in.")
        if room["status"] == "OCCUPIED":
            raise HotelError(f"Room {room['room_no']} is occupied; check the guest out first.")
        log_activity(self.db, self.actor, "ROOM_STATUS", f"{room['room_no']}: {room['status']} -> {status}")
        return self.db.update("rooms", "room_no", room["room_no"], {"status": status})

    # ---------------------------------------------------------- availability
    def bookings_overlapping(self, room_no: str, check_in: date, check_out: date,
                             exclude: str | None = None) -> list[dict]:
        ci, co = check_in.isoformat(), check_out.isoformat()
        return [b for b in self.db.find("bookings", room_no=room_no)
                if b["status"] in ACTIVE_BOOKING and b["booking_id"] != exclude
                and b["check_in"] < co and ci < b["check_out"]]

    def is_free(self, room_no: str, check_in, check_out, exclude: str | None = None) -> bool:
        room = self.get(room_no)
        if room["status"] == "MAINTENANCE":
            return False
        return not self.bookings_overlapping(room["room_no"], parse_date(check_in), parse_date(check_out), exclude)

    def available(self, check_in, check_out, category: str | None = None, guests: int = 1,
                  allow_past: bool = False) -> list[dict]:
        ci, co = validate_stay(check_in, check_out, allow_past)
        out = []
        for room in self.list(category):
            if guests > self.capacity(room) + 1:          # +1 with an extra bed
                continue
            if self.is_free(room["room_no"], ci, co):
                out.append(room)
        return out

    def summary(self) -> dict:
        rooms = self.list()
        return {"total": len(rooms), "by_status": dict(Counter(r["status"] for r in rooms)),
                "by_category": dict(Counter(r["category"] for r in rooms))}
