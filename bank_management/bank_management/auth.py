"""auth.py — customer PIN login, admin login, PIN change, lockout on wrong PINs."""
from __future__ import annotations

from database import JSONDatabase
from utils import (AccountFrozenError, AccountNotFoundError, AuthenticationError,
                   DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, MAX_PIN_ATTEMPTS,
                   ValidationError, hash_secret, now_str, validate_pin, verify_secret)


class AuthManager:
    def __init__(self, db: JSONDatabase):
        self.db = db
        self._ensure_default_admin()

    # ------------------------------------------------------------ admins
    def _ensure_default_admin(self) -> None:
        if not self.db.all("admins"):
            h, s = hash_secret(DEFAULT_ADMIN_PASSWORD)
            self.db.insert("admins", {"username": DEFAULT_ADMIN_USERNAME, "password_hash": h,
                                      "salt": s, "created_at": now_str(), "last_login": None})

    def admin_login(self, username: str, password: str) -> dict:
        admin = self.db.find_one("admins", username=str(username).strip().lower())
        if not admin or not verify_secret(password, admin["password_hash"], admin["salt"]):
            raise AuthenticationError("Invalid admin credentials.")
        self.db.update("admins", "username", admin["username"], {"last_login": now_str()})
        return admin

    def change_admin_password(self, username: str, old: str, new: str) -> None:
        self.admin_login(username, old)
        if len(new) < 6 or new.isdigit() or new.isalpha():
            raise ValidationError("Password must be 6+ characters with letters and digits.")
        h, s = hash_secret(new)
        self.db.update("admins", "username", username, {"password_hash": h, "salt": s})

    # --------------------------------------------------------- customers
    def _customer(self, account_no: str) -> dict:
        c = self.db.find_one("customers", account_no=str(account_no).strip())
        if not c:
            raise AccountNotFoundError("Account not found.")
        return c

    def verify_pin(self, account_no: str, pin: str) -> dict:
        """Check a PIN. Wrong PINs are counted; after MAX_PIN_ATTEMPTS the
        account is frozen and only an admin can unfreeze it."""
        c = self._customer(account_no)
        if c["status"] != "ACTIVE":
            raise AccountFrozenError("Account is frozen. Please contact the bank administrator.")
        if verify_secret(str(pin), c["pin_hash"], c["pin_salt"]):
            if c.get("failed_attempts"):
                self.db.update("customers", "account_no", c["account_no"], {"failed_attempts": 0})
            return c
        attempts = c.get("failed_attempts", 0) + 1
        changes = {"failed_attempts": attempts}
        if attempts >= MAX_PIN_ATTEMPTS:
            changes.update(status="FROZEN", frozen_reason="Too many incorrect PIN attempts")
            self.db.update("customers", "account_no", c["account_no"], changes)
            raise AccountFrozenError(f"Incorrect PIN entered {MAX_PIN_ATTEMPTS} times. "
                                     "Account frozen — contact the bank administrator.")
        self.db.update("customers", "account_no", c["account_no"], changes)
        raise AuthenticationError(f"Incorrect PIN. {MAX_PIN_ATTEMPTS - attempts} attempt(s) left.")

    def login(self, account_no: str, pin: str) -> dict:
        c = self.verify_pin(account_no, pin)
        self.db.update("customers", "account_no", c["account_no"], {"last_login": now_str()})
        return c

    def change_pin(self, account_no: str, old_pin: str, new_pin: str, confirm_pin: str) -> None:
        self.verify_pin(account_no, old_pin)
        validate_pin(new_pin)
        if new_pin != confirm_pin:
            raise ValidationError("New PIN and confirmation do not match.")
        if new_pin == old_pin:
            raise ValidationError("New PIN must be different from the old PIN.")
        h, s = hash_secret(new_pin)
        self.db.update("customers", "account_no", account_no, {"pin_hash": h, "pin_salt": s})
