# Backup & Restore
# backup.py (Part 1)

import os
import shutil
from datetime import datetime


# ==========================================
# Folder Configuration
# ==========================================

DATA_FOLDER = "data"
BACKUP_FOLDER = "backups"

os.makedirs(BACKUP_FOLDER, exist_ok=True)


# ==========================================
# Create Backup
# ==========================================

def create_backup():

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

    shutil.copytree(
        DATA_FOLDER,
        destination
    )

    print("\n====================================")
    print("Backup Created Successfully")
    print("====================================")

    print("Location :", destination)


# ==========================================
# List Backups
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
# View Available Backups
# ==========================================

def view_backups():

    backups = list_backups()

    if len(backups) == 0:

        print("\nNo Backup Available.")

        return

    print("\n")
    print("=" * 60)
    print("         AVAILABLE BACKUPS")
    print("=" * 60)

    for index, backup in enumerate(backups, start=1):

        print(f"{index}. {backup}")


# ==========================================
# Restore Backup
# ==========================================

def restore_backup():

    backups = list_backups()

    if len(backups) == 0:

        print("\nNo Backup Available.")

        return

    print("\n========== RESTORE BACKUP ==========\n")

    for index, backup in enumerate(backups, start=1):

        print(f"{index}. {backup}")

    try:

        choice = int(
            input("\nSelect Backup : ")
        )

        selected = backups[choice - 1]

    except (ValueError, IndexError):

        print("Invalid Selection.")

        return

    source = os.path.join(
        BACKUP_FOLDER,
        selected
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

    for index, backup in enumerate(backups, start=1):

        print(f"{index}. {backup}")

    try:

        choice = int(
            input("\nSelect Backup : ")
        )

        selected = backups[choice - 1]

    except (ValueError, IndexError):

        print("Invalid Selection.")

        return

    shutil.rmtree(

        os.path.join(

            BACKUP_FOLDER,

            selected

        )

    )

    print("\nBackup Deleted Successfully.")


# ==========================================
# Backup Information
# ==========================================

def backup_information():

    backups = list_backups()

    print("\n")
    print("=" * 60)
    print("        BACKUP INFORMATION")
    print("=" * 60)

    print("Total Backups :", len(backups))

    if backups:

        print("Latest Backup :", backups[-1])

    else:

        print("Latest Backup : None")
# ==========================================
# Automatic Backup
# ==========================================

def automatic_backup():

    print("\nCreating Automatic Backup...")

    create_backup()

    print("Automatic Backup Completed Successfully.")


# ==========================================
# Export Database Backup
# ==========================================

def export_backup():

    create_backup()

    print("\nDatabase Export Completed.")

    print("Backup Saved Successfully.")


# ==========================================
# Backup Statistics
# ==========================================

def backup_statistics():

    backups = list_backups()

    total_size = 0

    for backup in backups:

        path = os.path.join(

            BACKUP_FOLDER,

            backup

        )

        for root, dirs, files in os.walk(path):

            for file in files:

                file_path = os.path.join(

                    root,

                    file

                )

                total_size += os.path.getsize(

                    file_path

                )

    print("\n")
    print("=" * 60)
    print("        BACKUP STATISTICS")
    print("=" * 60)

    print("Total Backups :", len(backups))

    print(

        "Backup Size  : {:.2f} KB".format(

            total_size / 1024

        )

    )


# ==========================================
# Backup Dashboard
# ==========================================

def backup_dashboard():

    backups = list_backups()

    print("\n")
    print("=" * 60)
    print("         BACKUP DASHBOARD")
    print("=" * 60)

    print("Available Backups :", len(backups))

    if backups:

        print("Latest Backup :", backups[-1])

    else:

        print("Latest Backup : None")


# ==========================================
# Verify Backup Folder
# ==========================================

def verify_backup_folder():

    if os.path.exists(BACKUP_FOLDER):

        print("\nBackup Folder Verified.")

    else:

        print("\nBackup Folder Missing.")


# ==========================================
# Backup Menu
# ==========================================

def backup_menu():

    while True:

        print("\n")
        print("=" * 60)
        print("        BACKUP MANAGEMENT")
        print("=" * 60)

        print("1. Create Backup")
        print("2. Restore Backup")
        print("3. View Available Backups")
        print("4. Delete Backup")
        print("5. Backup Information")
        print("6. Automatic Backup")
        print("7. Export Database Backup")
        print("8. Backup Statistics")
        print("9. Backup Dashboard")
        print("10. Verify Backup Folder")
        print("11. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            create_backup()

        elif choice == "2":

            restore_backup()

        elif choice == "3":

            view_backups()

        elif choice == "4":

            delete_backup()

        elif choice == "5":

            backup_information()

        elif choice == "6":

            automatic_backup()

        elif choice == "7":

            export_backup()

        elif choice == "8":

            backup_statistics()

        elif choice == "9":

            backup_dashboard()

        elif choice == "10":

            verify_backup_folder()

        elif choice == "11":

            print("\nReturning to Main Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    backup_menu()