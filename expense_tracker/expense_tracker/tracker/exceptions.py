"""Custom exception hierarchy for the Expense Tracker."""


class TrackerError(Exception):
    """Base class for all application errors."""


class ValidationError(TrackerError):
    """Raised when user input fails validation."""


class NotFoundError(TrackerError):
    """Raised when a requested record does not exist."""


class AuthenticationError(TrackerError):
    """Raised on bad credentials or unauthorised access."""


class DatabaseError(TrackerError):
    """Raised when the JSON store cannot be read or written."""


class BackupError(TrackerError):
    """Raised when backup or restore fails."""
