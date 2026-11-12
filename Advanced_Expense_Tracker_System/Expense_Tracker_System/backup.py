# Backup & Restore
# backup.py

import os
import shutil
from datetime import datetime

# ==========================================
# Folders
# ==========================================

DATA_FOLDER = "data"
BACKUP_FOLDER = "backups"

os.makedirs(BACKUP_FOLDER, exist_ok=True)


# ==========================================
# Backup Database
# ==========================================

def backup_database():

    if not os.path.exists(DATA_FOLDER):
        print("\nData folder not found.")
        return

    backup_name = datetime.now().strftime(
        "Backup_%Y%m%d_%H%M%S"
    )

    destination = os.path.join(
        BACKUP_FOLDER,
        backup_name
    )

    shutil.copytree(DATA_FOLDER, destination)

    print("\nDatabase Backup Created Successfully.")
    print("Location :", destination)


# ==========================================
# List Backups
# ==========================================

def list_backups():

    backups = []

    if not os.path.exists(BACKUP_FOLDER):
        return backups

    for folder in os.listdir(BACKUP_FOLDER):

        path = os.path.join(BACKUP_FOLDER, folder)

        if os.path.isdir(path):
            backups.append(folder)

    return backups


# ==========================================
# Restore Database
# ==========================================

def restore_database():

    backups = list_backups()

    if len(backups) == 0:
        print("\nNo Backup Found.")
        return

    print("\n========== AVAILABLE BACKUPS ==========")

    for i, backup in enumerate(backups, start=1):
        print(f"{i}. {backup}")

    try:

        choice = int(input("\nSelect Backup : "))

        backup_folder = backups[choice - 1]

    except:

        print("Invalid Selection.")
        return

    source = os.path.join(
        BACKUP_FOLDER,
        backup_folder
    )

    if os.path.exists(DATA_FOLDER):
        shutil.rmtree(DATA_FOLDER)

    shutil.copytree(source, DATA_FOLDER)

    print("\nDatabase Restored Successfully.")


# ==========================================
# Delete Backup
# ==========================================

def delete_backup():

    backups = list_backups()

    if len(backups) == 0:
        print("\nNo Backup Found.")
        return

    print("\n========== BACKUPS ==========")

    for i, backup in enumerate(backups, start=1):
        print(f"{i}. {backup}")

    try:

        choice = int(input("\nSelect Backup : "))

        folder = backups[choice - 1]

    except:

        print("Invalid Choice.")
        return

    shutil.rmtree(
        os.path.join(BACKUP_FOLDER, folder)
    )

    print("\nBackup Deleted Successfully.")


# ==========================================
# Backup Menu
# ==========================================

def backup_menu():

    while True:

        print("\n==============================")
        print("      BACKUP MANAGEMENT")
        print("==============================")

        print("1. Create Backup")
        print("2. Restore Backup")
        print("3. View Backups")
        print("4. Delete Backup")
        print("5. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            backup_database()

        elif choice == "2":

            restore_database()

        elif choice == "3":

            backups = list_backups()

            if backups:

                print("\nAvailable Backups\n")

                for backup in backups:
                    print(backup)

            else:

                print("\nNo Backups Available.")

        elif choice == "4":

            delete_backup()

        elif choice == "5":

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    backup_menu()