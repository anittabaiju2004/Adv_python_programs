"""Booking Management: reservations, cancellation (with policy), no-shows,
check-in, room change, extra charges, stay extension and check-out."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from .auth import log_activity
from .billing import BillingManager, compute_bill, price_nights
from .customers import CustomerManager
from .database import JSONDatabase
from .rooms import RoomManager, validate_stay
from .utils import (BOOKING_SOURCES, CHECK_IN_TIME, FREE_CANCELLATION_HOURS, MAX_NIGHTS, SERVICE_TYPES,
                    AvailabilityError, HotelError, NotFoundError, ValidationError, gst, now_str, parse_date,
                    validate_amount, validate_choice, validate_int, validate_text)


class BookingManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor
        self.rooms = RoomManager(db, actor)
        self.customers = CustomerManager(db, actor)
        self.billing = BillingManager(db, actor)

    # ------------------------------------------------------------- helpers
    def _next_id(self) -> str:
        nums = [int(b["booking_id"][2:]) for b in self.db.all("bookings")]
        return f"BK{(max(nums) + 1) if nums else 10001}"

    def get(self, booking_id: str) -> dict:
        b = self.db.find_one("bookings", booking_id=str(booking_id or "").strip().upper())
        if not b:
            raise NotFoundError(f"Booking '{booking_id}' not found.")
        return b

    def _save(self, b: dict, changes: dict, action: str, details: str = "") -> dict:
        changes["updated_at"] = now_str()
        log_activity(self.db, self.actor, action, f"{b['booking_id']} {details}".strip())
        return self.db.update("bookings", "booking_id", b["booking_id"], changes)

    # ------------------------------------------------------------- create
    def create(self, customer_id: str, room_no: str, check_in, check_out, adults=1, children=0,
               extra_bed: bool = False, discount_pct=0, source: str = "Walk-in", requests: str = "",
               allow_past: bool = False) -> dict:
        cust = self.customers.get(customer_id)
        room = self.rooms.get(room_no)
        ci, co = validate_stay(check_in, check_out, allow_past)
        adults = validate_int(adults, "Adults", 1, 6)
        children = validate_int(children or 0, "Children", 0, 4)
        cap = self.rooms.capacity(room) + (1 if extra_bed else 0)
        if adults + children > cap:
            raise ValidationError(f"Room {room['room_no']} ({room['category']}) holds {cap} guest(s)"
                                  + ("" if extra_bed else "; add an extra bed for one more") + ".")
        if room["status"] == "MAINTENANCE":
            raise AvailabilityError(f"Room {room['room_no']} is under maintenance.")
        clash = self.rooms.bookings_overlapping(room["room_no"], ci, co)
        if clash:
            raise AvailabilityError(f"Room {room['room_no']} is booked {clash[0]['check_in']} to "
                                    f"{clash[0]['check_out']} ({clash[0]['booking_id']}).")
        discount = float(discount_pct or 0)
        nights = price_nights(self.rooms.tariff(room), ci, co, bool(extra_bed), discount)
        b = {"booking_id": self._next_id(), "customer_id": cust["customer_id"], "guest_name": cust["name"],
             "room_no": room["room_no"], "category": room["category"], "check_in": ci.isoformat(),
             "check_out": co.isoformat(), "nights": len(nights), "adults": adults, "children": children,
             "extra_bed": bool(extra_bed), "discount_pct": discount,
             "source": validate_choice(source, BOOKING_SOURCES, "source"),
             "requests": validate_text(requests, "Special requests", 200), "nights_detail": nights,
             "charges": [], "status": "CONFIRMED", "created_by": self.actor, "created_at": now_str(),
             "updated_at": now_str(), "actual_check_in": None, "actual_check_out": None,
             "cancelled_at": None, "cancel_reason": None, "cancellation_fee": 0.0,
             "invoice_no": None, "invoice_date": None, "invoice": None}
        self.db.insert("bookings", b)
        log_activity(self.db, self.actor, "BOOKING_CREATED",
                     f"{b['booking_id']} room {room['room_no']} {b['check_in']}→{b['check_out']}")
        return b

    def estimate(self, booking: dict) -> dict:
        return compute_bill(booking, self.billing.payments(booking["booking_id"]))

    # ------------------------------------------------------------- queries
    def list(self, status: str | None = None, start=None, end=None) -> list[dict]:
        bs = self.db.all("bookings")
        if status:
            bs = [b for b in bs if b["status"] == status.upper()]
        if start:
            bs = [b for b in bs if b["check_out"] > parse_date(start).isoformat()]
        if end:
            bs = [b for b in bs if b["check_in"] <= parse_date(end).isoformat()]
        return sorted(bs, key=lambda b: (b["check_in"], b["booking_id"]))

    def search(self, keyword: str) -> list[dict]:
        k = str(keyword or "").strip().lower()
        cust_ids = {c["customer_id"] for c in self.customers.search(k)} if k else set()
        return [b for b in self.list() if k == b["booking_id"].lower() or k == b["room_no"].lower()
                or b["customer_id"] in cust_ids or k in b["guest_name"].lower()]

    def arrivals(self, day=None) -> list[dict]:
        d = parse_date(day or date.today()).isoformat()
        return [b for b in self.list("CONFIRMED") if b["check_in"] == d]

    def departures(self, day=None) -> list[dict]:
        d = parse_date(day or date.today()).isoformat()
        return [b for b in self.list("CHECKED_IN") if b["check_out"] == d]

    def in_house(self) -> list[dict]:
        return self.list("CHECKED_IN")

    # ----------------------------------------------------------- cancel
    def cancellation_quote(self, booking_id: str, at: datetime | None = None) -> dict:
        b = self.get(booking_id)
        if b["status"] != "CONFIRMED":
            raise HotelError(f"Only confirmed bookings can be cancelled (this one is {b['status']}).")
        at = at or datetime.now()
        arrival = datetime.strptime(f"{b['check_in']} {CHECK_IN_TIME}", "%Y-%m-%d %H:%M")
        hours = (arrival - at).total_seconds() / 3600
        first = b["nights_detail"][0]
        fee = 0.0 if hours >= FREE_CANCELLATION_HOURS else round(first["tariff"] + first["gst"], 2)
        paid = self.billing.paid(b["booking_id"])
        return {"hours_before": round(hours, 1), "fee": fee, "paid": paid,
                "refund": round(max(0.0, paid - fee), 2), "due": round(max(0.0, fee - paid), 2)}

    def cancel(self, booking_id: str, reason: str, refund_mode: str = "Cash", at: datetime | None = None) -> dict:
        """Cancel a confirmed booking. Free if at least FREE_CANCELLATION_HOURS before
        check-in time; otherwise the first night (with GST) is retained."""
        q = self.cancellation_quote(booking_id, at)
        b = self.get(booking_id)
        if q["refund"]:
            self.billing.refund(b["booking_id"], q["refund"], refund_mode, "Cancellation refund")
        retained = round(min(q["fee"], q["paid"]), 2)
        self._save(b, {"status": "CANCELLED", "cancelled_at": (at or datetime.now()).isoformat(timespec="seconds"),
                       "cancel_reason": validate_text(reason, "Reason", 120) or "Guest request",
                       "cancellation_fee": retained}, "BOOKING_CANCELLED", f"fee {retained:.2f}")
        return {**q, "retained": retained}

    def mark_no_shows(self, today: date | None = None, refund_mode: str = "Cash") -> list[dict]:
        """Confirmed bookings whose check-in date has passed become NO_SHOW;
        the first night is retained from any advance, the rest refunded."""
        today = today or date.today()
        out = []
        for b in self.list("CONFIRMED"):
            if b["check_in"] < today.isoformat():
                first = b["nights_detail"][0]
                paid = self.billing.paid(b["booking_id"])
                fee = round(min(paid, first["tariff"] + first["gst"]), 2)
                if paid - fee > 0.005:
                    self.billing.refund(b["booking_id"], round(paid - fee, 2), refund_mode, "No-show refund")
                out.append(self._save(b, {"status": "NO_SHOW", "cancellation_fee": fee,
                                          "cancelled_at": now_str(), "cancel_reason": "No-show"}, "NO_SHOW"))
        return out

    # ---------------------------------------------------------- check-in
    def check_in(self, booking_id: str, on: datetime | None = None) -> dict:
        b = self.get(booking_id)
        on = on or datetime.now()
        if b["status"] != "CONFIRMED":
            raise HotelError(f"Booking is {b['status']}; cannot check in.")
        d = on.date().isoformat()
        if d < b["check_in"]:
            raise HotelError(f"Check-in date is {b['check_in']}. For an early arrival, amend the booking dates.")
        if d >= b["check_out"]:
            raise HotelError("The booked stay has already ended; mark it as a no-show or rebook.")
        cust = self.customers.get(b["customer_id"])
        if not cust["id_number"]:
            raise HotelError("Record the guest's ID proof (Customer Management) before check-in.")
        room = self.rooms.get(b["room_no"])
        if room["status"] != "AVAILABLE":
            raise HotelError(f"Room {room['room_no']} is {room['status']}. Mark it clean or change the room.")
        self.db.update("rooms", "room_no", room["room_no"], {"status": "OCCUPIED"})
        return self._save(b, {"status": "CHECKED_IN", "actual_check_in": on.isoformat(timespec="seconds")},
                          "CHECKED_IN", f"room {room['room_no']}")

    def change_room(self, booking_id: str, new_room_no: str, reprice: bool = False) -> dict:
        b = self.get(booking_id)
        if b["status"] not in ("CONFIRMED", "CHECKED_IN"):
            raise HotelError("Room can only be changed for confirmed or in-house bookings.")
        new = self.rooms.get(new_room_no)
        if new["room_no"] == b["room_no"]:
            raise ValidationError("That is the current room.")
        start = max(parse_date(b["check_in"]), date.today()) if b["status"] == "CHECKED_IN" else parse_date(b["check_in"])
        end = parse_date(b["check_out"])
        if new["status"] == "MAINTENANCE" or self.rooms.bookings_overlapping(new["room_no"], start, end, b["booking_id"]):
            raise AvailabilityError(f"Room {new['room_no']} is not free for the remaining stay.")
        if self.rooms.capacity(new) + (1 if b["extra_bed"] else 0) < b["adults"] + b["children"]:
            raise ValidationError(f"Room {new['room_no']} is too small for this party.")
        changes = {"room_no": new["room_no"], "category": new["category"]}
        if reprice:
            done = [n for n in b["nights_detail"] if n["date"] < start.isoformat()]
            changes["nights_detail"] = done + price_nights(self.rooms.tariff(new), start, end, b["extra_bed"],
                                                           b["discount_pct"])
        if b["status"] == "CHECKED_IN":
            if new["status"] != "AVAILABLE":
                raise HotelError(f"Room {new['room_no']} is {new['status']}.")
            self.db.update("rooms", "room_no", b["room_no"], {"status": "CLEANING"})
            self.db.update("rooms", "room_no", new["room_no"], {"status": "OCCUPIED"})
        return self._save(b, changes, "ROOM_CHANGED", f"{b['room_no']} -> {new['room_no']}")

    # ------------------------------------------------------------ in-house
    def add_charge(self, booking_id: str, service: str, description: str, amount) -> dict:
        b = self.get(booking_id)
        if b["status"] != "CHECKED_IN":
            raise HotelError("Charges can only be added while the guest is checked in.")
        service = validate_choice(service, SERVICE_TYPES, "service")
        amount = validate_amount(amount, "Amount", 1, 2_00_000)
        rate = SERVICE_TYPES[service]["gst"]
        charge = {"id": f"CH{len(b['charges']) + 1:03d}", "date": date.today().isoformat(), "service": service,
                  "description": validate_text(description, "Description", 80, required=True),
                  "amount": amount, "gst_rate": rate, "gst": gst(amount, rate), "by": self.actor}
        self._save(b, {"charges": b["charges"] + [charge]}, "CHARGE_ADDED", f"{service} {amount:.2f}")
        return charge

    def remove_charge(self, booking_id: str, charge_id: str) -> None:
        b = self.get(booking_id)
        if b["status"] != "CHECKED_IN":
            raise HotelError("Charges can only be changed during the stay.")
        kept = [c for c in b["charges"] if c["id"] != charge_id.upper()]
        if len(kept) == len(b["charges"]):
            raise NotFoundError(f"Charge {charge_id} not found.")
        self._save(b, {"charges": kept}, "CHARGE_REMOVED", charge_id.upper())

    def extend(self, booking_id: str, new_check_out) -> dict:
        b = self.get(booking_id)
        if b["status"] not in ("CONFIRMED", "CHECKED_IN"):
            raise HotelError("Only confirmed or in-house bookings can be extended.")
        old_co, new_co = parse_date(b["check_out"]), parse_date(new_check_out, "New check-out date")
        if new_co <= old_co:
            raise ValidationError("New check-out must be after the current check-out.")
        if (new_co - parse_date(b["check_in"])).days > MAX_NIGHTS:
            raise ValidationError(f"A stay can be at most {MAX_NIGHTS} nights.")
        clash = self.rooms.bookings_overlapping(b["room_no"], old_co, new_co, b["booking_id"])
        if clash:
            raise AvailabilityError(f"Room {b['room_no']} is booked from {clash[0]['check_in']} "
                                    f"({clash[0]['booking_id']}). Change the room to extend.")
        room = self.rooms.get(b["room_no"])
        extra = price_nights(self.rooms.tariff(room), old_co, new_co, b["extra_bed"], b["discount_pct"])
        nd = b["nights_detail"] + extra
        return self._save(b, {"check_out": new_co.isoformat(), "nights_detail": nd, "nights": len(nd)},
                          "STAY_EXTENDED", f"to {new_co.isoformat()}")

    # ---------------------------------------------------------- check-out
    def _trimmed(self, b: dict, on: date) -> dict:
        """Booking as it would be billed if the guest leaves on `on` (early departure
        bills only the nights actually used, minimum one)."""
        if on.isoformat() >= b["check_out"]:
            return b
        used = max(1, (on - parse_date(b["check_in"])).days)
        nd = b["nights_detail"][:used]
        return {**b, "nights_detail": nd, "nights": len(nd),
                "check_out": (parse_date(b["check_in"]) + timedelta(days=used)).isoformat()}

    def checkout_preview(self, booking_id: str, on: date | None = None) -> dict:
        b = self.get(booking_id)
        if b["status"] != "CHECKED_IN":
            raise HotelError(f"Booking is {b['status']}; only checked-in guests can check out.")
        t = self._trimmed(b, on or date.today())
        return {"booking": t, "bill": compute_bill(t, self.billing.payments(b["booking_id"])),
                "early": t["nights"] < b["nights"]}

    def check_out(self, booking_id: str, on: datetime | None = None, refund_mode: str = "Cash") -> dict:
        """Close the stay: bill only used nights, require the balance to be settled
        (excess advance is refunded), issue the invoice and send the room to cleaning."""
        on = on or datetime.now()
        prev = self.checkout_preview(booking_id, on.date())
        bill, t = prev["bill"], prev["booking"]
        if bill["balance"] > 0.005:
            raise HotelError(f"Balance due {bill['balance']:,.2f}. Collect payment before check-out.")
        if bill["balance"] < -0.005:
            self.billing.refund(t["booking_id"], -bill["balance"], refund_mode, "Excess advance refund")
            bill = compute_bill(t, self.billing.payments(t["booking_id"]))
        inv_no = self.billing.next_invoice_no(on.date())
        self.db.update("rooms", "room_no", t["room_no"], {"status": "CLEANING"})
        return self._save(self.get(booking_id),
                          {"status": "CHECKED_OUT", "actual_check_out": on.isoformat(timespec="seconds"),
                           "check_out": t["check_out"], "nights_detail": t["nights_detail"], "nights": t["nights"],
                           "invoice_no": inv_no, "invoice_date": on.date().isoformat(), "invoice": bill},
                          "CHECKED_OUT", inv_no)
