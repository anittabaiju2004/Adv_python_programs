# JSON database
# database.py

import json
import os


# ==========================================
# Data Folder
# ==========================================

DATA_FOLDER = "data"

os.makedirs(DATA_FOLDER, exist_ok=True)


# ==========================================
# Database Files
# ==========================================

EMPLOYEE_FILE = os.path.join(
    DATA_FOLDER,
    "employees.json"
)

ADMIN_FILE = os.path.join(
    DATA_FOLDER,
    "admins.json"
)

ATTENDANCE_FILE = os.path.join(
    DATA_FOLDER,
    "attendance.json"
)

LEAVE_FILE = os.path.join(
    DATA_FOLDER,
    "leave.json"
)

PAYROLL_FILE = os.path.join(
    DATA_FOLDER,
    "payroll.json"
)


# ==========================================
# Initialize Database
# ==========================================

def initialize_database():

    files = [

        EMPLOYEE_FILE,
        ATTENDANCE_FILE,
        LEAVE_FILE,
        PAYROLL_FILE

    ]

    for file in files:

        if not os.path.exists(file):

            with open(
                file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    [],
                    f,
                    indent=4
                )

    if not os.path.exists(ADMIN_FILE):

        default_admin = [

            {

                "username": "admin",
                "password": "admin123"

            }

        ]

        with open(
            ADMIN_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                default_admin,
                f,
                indent=4
            )


# ==========================================
# Employee Functions
# ==========================================

def get_employees():

    try:

        with open(
            EMPLOYEE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except (

        FileNotFoundError,
        json.JSONDecodeError

    ):

        return []


def save_employees(employees):

    with open(
        EMPLOYEE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            employees,
            f,
            indent=4
        )


# ==========================================
# Admin Functions
# ==========================================

def get_admins():

    try:

        with open(
            ADMIN_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except (

        FileNotFoundError,
        json.JSONDecodeError

    ):

        return []


def save_admins(admins):

    with open(
        ADMIN_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            admins,
            f,
            indent=4
        )


# ==========================================
# Attendance Functions
# ==========================================

def get_attendance():

    try:

        with open(
            ATTENDANCE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except (

        FileNotFoundError,
        json.JSONDecodeError

    ):

        return []


def save_attendance(attendance):

    with open(
        ATTENDANCE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            attendance,
            f,
            indent=4
        )


# ==========================================
# Leave Functions
# ==========================================

def get_leave_records():

    try:

        with open(
            LEAVE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except (

        FileNotFoundError,
        json.JSONDecodeError

    ):

        return []


def save_leave_records(records):

    with open(
        LEAVE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            records,
            f,
            indent=4
        )


# ==========================================
# Payroll Functions
# ==========================================

def get_payroll():

    try:

        with open(
            PAYROLL_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except (

        FileNotFoundError,
        json.JSONDecodeError

    ):

        return []


def save_payroll(payroll):

    with open(
        PAYROLL_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            payroll,
            f,
            indent=4
        )


# ==========================================
# Database Information
# ==========================================

def database_information():

    print("\n")
    print("=" * 60)
    print("        DATABASE INFORMATION")
    print("=" * 60)

    print("Employees :", len(get_employees()))
    print("Admins    :", len(get_admins()))
    print("Attendance:", len(get_attendance()))
    print("Leaves    :", len(get_leave_records()))
    print("Payroll   :", len(get_payroll()))

    print("=" * 60)


# ==========================================
# Reset Database
# ==========================================

def reset_database():

    save_employees([])

    save_attendance([])

    save_leave_records([])

    save_payroll([])

    save_admins([

        {

            "username": "admin",
            "password": "admin123"

        }

    ])

    print("\nDatabase Reset Successfully.")


# ==========================================
# Export Database
# ==========================================

def export_database():

    return {

        "employees": get_employees(),

        "admins": get_admins(),

        "attendance": get_attendance(),

        "leave": get_leave_records(),

        "payroll": get_payroll()

    }


# ==========================================
# Import Database
# ==========================================

def import_database(data):

    save_employees(

        data.get(
            "employees",
            []
        )
    )

    save_admins(

        data.get(
            "admins",
            []
        )
    )

    save_attendance(

        data.get(
            "attendance",
            []
        )
    )

    save_leave_records(

        data.get(
            "leave",
            []
        )
    )

    save_payroll(

        data.get(
            "payroll",
            []
        )
    )

    print("\nDatabase Imported Successfully.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    initialize_database()

    database_information()