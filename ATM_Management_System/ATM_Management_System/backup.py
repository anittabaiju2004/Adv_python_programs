# Backup & restore
# backup.py

import os
import shutil
from datetime import datetime


# ==========================================
# Folder Paths
# ==========================================

DATA_FOLDER = "data"

BACKUP_FOLDER = "backups"

os.makedirs(BACKUP_FOLDER, exist_ok=True)


# ==========================================
# Create Backup
# ==========================================

def backup_database():

    if not os.path.exists(DATA_FOLDER):

        print("\nData Folder Not Found.")

        return

    backup_name = datetime.now().strftime(
        "Backup_%Y%m%d_%H%M%S"
    )

    destination = os.path.join(
        BACKUP_FOLDER,
        backup_name
    )

    shutil.copytree(DATA_FOLDER, destination)

    print("\n===================================")
    print("Database Backup Created Successfully")
    print("===================================")
    print("Backup Folder :", destination)


# ==========================================
# View Backups
# ==========================================

def list_backups():

    backups = []

    if not os.path.exists(BACKUP_FOLDER):

        return backups

    for folder in os.listdir(BACKUP_FOLDER):

        path = os.path.join(
            BACKUP_FOLDER,
            folder
        )

        if os.path.isdir(path):

            backups.append(folder)

    return backups


# ==========================================
# Display Backups
# ==========================================

def view_backups():

    backups = list_backups()

    if len(backups) == 0:

        print("\nNo Backups Available.")

        return

    print("\n========== AVAILABLE BACKUPS ==========\n")

    for i, backup in enumerate(backups, start=1):

        print(f"{i}. {backup}")


# ==========================================
# Restore Backup
# ==========================================

def restore_database():

    backups = list_backups()

    if len(backups) == 0:

        print("\nNo Backup Found.")

        return

    print("\n========== RESTORE DATABASE ==========\n")

    for i, backup in enumerate(backups, start=1):

        print(f"{i}. {backup}")

    try:

        choice = int(input("\nSelect Backup : "))

        folder = backups[choice - 1]

    except:

        print("Invalid Choice.")

        return

    source = os.path.join(
        BACKUP_FOLDER,
        folder
    )

    if os.path.exists(DATA_FOLDER):

        shutil.rmtree(DATA_FOLDER)

    shutil.copytree(
        source,
        DATA_FOLDER
    )

    print("\nDatabase Restored Successfully.")


# ==========================================
# Delete Backup
# ==========================================

def delete_backup():

    backups = list_backups()

    if len(backups) == 0:

        print("\nNo Backup Available.")

        return

    print("\n========== DELETE BACKUP ==========\n")

    for i, backup in enumerate(backups, start=1):

        print(f"{i}. {backup}")

    try:

        choice = int(input("\nSelect Backup : "))

        folder = backups[choice - 1]

    except:

        print("Invalid Choice.")

        return

    shutil.rmtree(

        os.path.join(
            BACKUP_FOLDER,
            folder
        )

    )

    print("\nBackup Deleted Successfully.")


# ==========================================
# Backup Information
# ==========================================

def backup_information():

    backups = list_backups()

    print("\n========== BACKUP INFORMATION ==========\n")

    print("Total Backups :", len(backups))

    if backups:

        print("\nLatest Backup :", backups[-1])


# ==========================================
# Backup Menu
# ==========================================

def backup_menu():

    while True:

        print("\n")
        print("=" * 50)
        print("       DATABASE BACKUP MENU")
        print("=" * 50)

        print("1. Create Backup")
        print("2. Restore Backup")
        print("3. View Backups")
        print("4. Delete Backup")
        print("5. Backup Information")
        print("6. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            backup_database()

        elif choice == "2":

            restore_database()

        elif choice == "3":

            view_backups()

        elif choice == "4":

            delete_backup()

        elif choice == "5":

            backup_information()

        elif choice == "6":

            print("\nReturning...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    backup_menu()