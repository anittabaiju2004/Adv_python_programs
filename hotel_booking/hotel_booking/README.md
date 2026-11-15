# Hotel Booking Management System

**Advanced Hotel Room Reservation Management Using Python and JSON File Handling**

A menu-driven hotel front-office application for *Hotel Malabar Residency*. It covers:

- **Reservations:** availability search, room booking, cancellation with a policy, no-shows.
- **Guest stays:** check-in with ID proof, room changes, extensions, room service, laundry and spa charges.
- **Billing:** check-out with **GST tax invoices (PDF)**, payments and refunds.
- **Hotel operations:** housekeeping, staff with role-based access, revenue and occupancy reports, an admin activity log, and backup & restore.

All data is stored permanently in JSON files.

---

## Quick start

```bash
pip install -r requirements.txt
python seed_demo.py      # optional: 20 rooms, staff, guests and ~5 weeks of bookings (takes ~15 s)
python main.py
```

| Role | Login | Can use |
|---|---|---|
| Admin | `admin` / `admin123` | Everything, including staff management, activity log, backup & restore |
| Manager | `manager` / `manager1` | Front desk, rooms (add/edit), customers, reports, discounts, no-shows |
| Receptionist | `reception` / `front123` | Front desk, customers, room status |
| Housekeeping | `housekeeping` / `clean123` | Room status board, marking rooms clean |

The demo logins exist only after running `seed_demo.py`; `admin` is always created on
first run. Run the tests with `python -m pytest -q` (14 tests).

---

## Project structure

```
hotel_booking/
├── main.py                Entry point
├── seed_demo.py           Demo data loader
├── hotel/
│   ├── rooms.py           Room Management (categories, tariffs, availability, housekeeping)
│   ├── bookings.py        Booking Management (book, cancel, no-show, check-in/out, extend, change room)
│   ├── customers.py       Customer Management (guests, ID proof, booking history)
│   ├── billing.py         Payment & Invoice (pricing, GST, payments, refunds, PDF invoice)
│   ├── staff.py           Staff Management
│   ├── auth.py            Authentication (hashing, roles & permissions, lockout, activity log)
│   ├── admin.py           Admin Panel (dashboard, statistics, activity log)
│   ├── reports.py         Reports (revenue, occupancy, CSV, PDF)
│   ├── backup.py          Backup & Restore
│   ├── database.py        JSON Database
│   ├── utils.py           Hotel settings, GST rules, validation, helpers
│   └── cli.py             Role-based menu interface
├── tests/test_hotel.py    Unit tests (pytest)
├── data/                  users, rooms, customers, bookings, payments, activity (.json)
├── backups/               Backup zip files
└── reports/               Reports; invoices in reports/invoices/
```

---

## Modules

| Module | What it does |
|---|---|
| **Room Management** | Four room categories (Standard ₹2,500, Deluxe ₹4,500, Executive ₹6,800, Suite ₹9,500), each with a guest limit and amenities. Rooms can have a custom tariff. Availability search by dates, category and party size; a room status board by floor; statuses Available → Occupied → Cleaning → Available, plus Maintenance |
| **Booking Management** | Bookings are priced **night by night**: weekend (Fri/Sat) +10 %, optional extra bed ₹800, and manager discount up to 30 %. Double-booking is prevented. **Cancellation policy:** free up to 48 h before check-in, otherwise the first night is retained and the rest refunded. No-shows are processed the same way. Also extend stay, change room (keep or re-price) and arrivals/departures/in-house lists |
| **Check-in / Check-out** | Check-in requires guest ID proof and a clean room. Service charges are added during the stay. Check-out bills only the nights used (early departure), collects the balance, refunds any excess advance, issues the invoice and sends the room to housekeeping |
| **Customer Management** | Guest registration with Aadhaar, Passport, Driving Licence or Voter ID validation, international phone numbers, and company GSTIN. Search, update, and booking history (stays, nights, total spent, cancellations). Guests with history can't be deleted |
| **Payment & Invoice** | Payments by Cash, UPI, Card or Net Banking, with a reference required for non-cash payments. Advances, settlements and refunds. **GST tax invoice PDF** with SAC codes, a CGST/SGST split per rate, round-off and the amount in words. Invoice numbers run per financial year (`INV/2026-27/0001`). A pro-forma bill is available during the stay |
| **Staff Management** | Add staff with role, shift and salary, plus a login with a temporary password (changed at first login). Update, activate/deactivate, reset password or unlock. The last admin can't be removed |
| **Authentication** | PBKDF2-HMAC-SHA256 password hashing; lockout after 5 failed attempts; role-based permissions decide which menus each user sees |
| **Admin Panel** | Dashboard showing tonight's occupancy, arrivals and departures, in-house guests, overdue check-outs, pending no-shows and today's collections. Also an activity log of who did what and when, and system statistics |
| **Reports** | **Revenue:** room revenue, extras by service, cancellation fees, GST collected, payments by mode, refunds, and revenue by category. **Occupancy:** nightly and by category, average and peak, **ADR** and **RevPAR**. A PDF performance report with a chart, and CSV exports for bookings, customers (ID numbers masked), daily revenue and daily occupancy |
| **Backup & Restore** | Timestamped zip backups. Restore checks the file first and automatically backs up the current data so a restore can be undone |
| **JSON Database** | Six JSON files with atomic writes (temporary file, then `os.replace`) and a clear error if a file is damaged |

### GST rules used
Room tariff GST is decided per night from the final tariff (after weekend, extra bed and
discount), following the rates in force since **22 September 2025**:

| Item | GST |
|---|---|
| Room tariff up to ₹7,500 per night | 5 % |
| Room tariff above ₹7,500 per night | 18 % |
| Food & beverage at a hotel with any room above ₹7,500 ("specified premises") | 18 % (otherwise 5 %) |
| Laundry, spa and other services | 18 % |

GST is shown as CGST + SGST (half each), since the hotel and guest are treated as being
in the same state. All rates and thresholds are in `hotel/utils.py`. The GSTIN printed on
invoices is a sample. The tax rules are simplified for an academic project; check the
current rates before real use.

### Exception handling
All errors derive from `HotelError` (`ValidationError`, `NotFoundError`,
`AuthenticationError`, `PermissionDenied`, `AvailabilityError`, `DatabaseError`,
`BackupError`) and are shown as friendly messages instead of crashing.

### Configuration
Hotel name, address and GSTIN, room categories and rates, weekend surcharge, extra bed
rate, cancellation window, GST rules, payment modes and role permissions are all set in
`hotel/utils.py`. Environment variables `HOTEL_DATA_DIR`, `HOTEL_BACKUP_DIR` and
`HOTEL_REPORT_DIR` override the storage folders.

---

## Technologies
Python 3.10+, JSON, OOP, `datetime`, `hashlib`/`hmac`, `csv`, `shutil`/`zipfile`,
ReportLab (PDF and charts), pytest. IDE: Visual Studio Code.

## Future enhancements
SQLite/MySQL · Tkinter GUI · Django web application with online booking · Payment
gateway · Email/SMS confirmations and invoices · Cloud database · Channel-manager
integration (OTA bookings)
