# transaction.py (Part 1)

from database import (
    get_transactions,
    save_transactions
)

from utils import (
    generate_transaction_id,
    current_datetime,
    print_receipt
)


# ==========================================
# Record Transaction
# ==========================================

def record_transaction(
    account_number,
    transaction_type,
    amount,
    balance,
    receiver_account=None
):

    transactions = get_transactions()

    transaction = {

        "transaction_id": generate_transaction_id(),
        "account_number": account_number,
        "type": transaction_type,
        "amount": amount,
        "balance": balance,
        "receiver_account": receiver_account,
        "date": current_datetime()

    }

    transactions.append(transaction)

    save_transactions(transactions)


# ==========================================
# Deposit Transaction
# ==========================================

def deposit_transaction(

    account_number,
    amount,
    balance

):

    record_transaction(

        account_number=account_number,
        transaction_type="Deposit",
        amount=amount,
        balance=balance

    )

    print("\nDeposit Recorded Successfully.")

    print_receipt(

        account_number,
        "Deposit",
        amount,
        balance

    )


# ==========================================
# Withdraw Transaction
# ==========================================

def withdraw_transaction(

    account_number,
    amount,
    balance

):

    record_transaction(

        account_number=account_number,
        transaction_type="Withdraw",
        amount=amount,
        balance=balance

    )

    print("\nWithdrawal Recorded Successfully.")

    print_receipt(

        account_number,
        "Withdraw",
        amount,
        balance

    )


# ==========================================
# Transfer Transaction
# ==========================================

def transfer_transaction(

    sender_account,
    receiver_account,
    amount,
    sender_balance

):

    record_transaction(

        account_number=sender_account,
        transaction_type="Transfer",
        amount=amount,
        balance=sender_balance,
        receiver_account=receiver_account

    )

    print("\nTransfer Recorded Successfully.")

    print_receipt(

        sender_account,
        "Transfer",
        amount,
        sender_balance

    )


# ==========================================
# View All Transactions
# ==========================================

def view_transactions():

    transactions = get_transactions()

    if len(transactions) == 0:

        print("\nNo Transactions Available.")

        return

    print("\n========== ALL TRANSACTIONS ==========\n")

    for transaction in transactions:

        print("-" * 60)

        print("Transaction ID :", transaction["transaction_id"])
        print("Account Number :", transaction["account_number"])
        print("Type           :", transaction["type"])
        print("Amount         : ₹", transaction["amount"])
        print("Balance        : ₹", transaction["balance"])

        if transaction["receiver_account"]:

            print(
                "Receiver Account :",
                transaction["receiver_account"]
            )

        print("Date           :", transaction["date"])
# ==========================================
# Search Transaction
# ==========================================

def search_transaction():

    transactions = get_transactions()

    transaction_id = input(
        "\nEnter Transaction ID : "
    ).strip()

    for transaction in transactions:

        if transaction["transaction_id"] == transaction_id:

            print("\n========== TRANSACTION DETAILS ==========\n")

            print("Transaction ID :", transaction["transaction_id"])
            print("Account Number :", transaction["account_number"])
            print("Type           :", transaction["type"])
            print("Amount         : ₹", transaction["amount"])
            print("Balance        : ₹", transaction["balance"])

            if transaction.get("receiver_account"):

                print(
                    "Receiver Account :",
                    transaction["receiver_account"]
                )

            print("Date           :", transaction["date"])

            return

    print("\nTransaction Not Found.")


# ==========================================
# Transaction History
# ==========================================

def transaction_history():

    transactions = get_transactions()

    account_number = input(
        "\nEnter Account Number : "
    ).strip()

    history = []

    for transaction in transactions:

        if transaction["account_number"] == account_number:

            history.append(transaction)

    if len(history) == 0:

        print("\nNo Transactions Found.")

        return

    print("\n========== TRANSACTION HISTORY ==========\n")

    for transaction in history:

        print("-" * 60)

        print("Transaction ID :", transaction["transaction_id"])
        print("Type           :", transaction["type"])
        print("Amount         : ₹", transaction["amount"])
        print("Balance        : ₹", transaction["balance"])

        if transaction.get("receiver_account"):

            print(
                "Receiver Account :",
                transaction["receiver_account"]
            )

        print("Date           :", transaction["date"])


# ==========================================
# Mini Statement
# ==========================================

def mini_statement():

    transactions = get_transactions()

    account_number = input(
        "\nEnter Account Number : "
    ).strip()

    history = []

    for transaction in transactions:

        if transaction["account_number"] == account_number:

            history.append(transaction)

    if len(history) == 0:

        print("\nNo Transactions Found.")

        return

    print("\n========== MINI STATEMENT ==========\n")

    recent_transactions = history[-5:]

    for transaction in recent_transactions:

        print("-" * 50)

        print("Transaction ID :", transaction["transaction_id"])
        print("Type           :", transaction["type"])
        print("Amount         : ₹", transaction["amount"])
        print("Balance        : ₹", transaction["balance"])

        if transaction.get("receiver_account"):

            print(
                "Receiver Account :",
                transaction["receiver_account"]
            )

        print("Date           :", transaction["date"])

    print("-" * 50)
    print(f"Total Transactions : {len(history)}")


# ==========================================
# Account Transaction Summary
# ==========================================

def account_transaction_summary():

    transactions = get_transactions()

    account_number = input(
        "\nEnter Account Number : "
    ).strip()

    deposits = 0
    withdrawals = 0
    transfers = 0

    deposit_amount = 0
    withdrawal_amount = 0
    transfer_amount = 0

    for transaction in transactions:

        if transaction["account_number"] == account_number:

            if transaction["type"] == "Deposit":

                deposits += 1
                deposit_amount += transaction["amount"]

            elif transaction["type"] == "Withdraw":

                withdrawals += 1
                withdrawal_amount += transaction["amount"]

            elif transaction["type"] == "Transfer":

                transfers += 1
                transfer_amount += transaction["amount"]

    print("\n========== ACCOUNT TRANSACTION SUMMARY ==========\n")

    print("Account Number        :", account_number)

    print(f"Deposit Count         : {deposits}")
    print(f"Deposit Amount        : ₹{deposit_amount:.2f}")

    print(f"\nWithdrawal Count      : {withdrawals}")
    print(f"Withdrawal Amount     : ₹{withdrawal_amount:.2f}")

    print(f"\nTransfer Count        : {transfers}")
    print(f"Transfer Amount       : ₹{transfer_amount:.2f}")

    print(
        f"\nTotal Transactions    : "
        f"{deposits + withdrawals + transfers}"
    )
# ==========================================
# Daily Transactions
# ==========================================

def daily_transactions():

    transactions = get_transactions()

    date = input("\nEnter Date (YYYY-MM-DD): ").strip()

    found = False
    total = 0

    print("\n========== DAILY TRANSACTIONS ==========\n")

    for transaction in transactions:

        if transaction["date"].startswith(date):

            found = True

            print("-" * 60)
            print("Transaction ID :", transaction["transaction_id"])
            print("Account Number :", transaction["account_number"])
            print("Type           :", transaction["type"])
            print("Amount         : ₹", transaction["amount"])
            print("Date           :", transaction["date"])

            total += transaction["amount"]

    if not found:

        print("No Transactions Found.")

    else:

        print("\nTotal Amount : ₹", total)


# ==========================================
# Monthly Transactions
# ==========================================

def monthly_transactions():

    transactions = get_transactions()

    month = input("\nEnter Month (YYYY-MM): ").strip()

    found = False
    total = 0

    print("\n========== MONTHLY TRANSACTIONS ==========\n")

    for transaction in transactions:

        if transaction["date"].startswith(month):

            found = True

            print("-" * 60)
            print("Transaction ID :", transaction["transaction_id"])
            print("Account Number :", transaction["account_number"])
            print("Type           :", transaction["type"])
            print("Amount         : ₹", transaction["amount"])
            print("Date           :", transaction["date"])

            total += transaction["amount"]

    if not found:

        print("No Transactions Found.")

    else:

        print("\nTotal Monthly Amount : ₹", total)


# ==========================================
# Transaction Statistics
# ==========================================

def transaction_statistics():

    transactions = get_transactions()

    deposits = 0
    withdrawals = 0
    transfers = 0

    deposit_amount = 0
    withdraw_amount = 0
    transfer_amount = 0

    for transaction in transactions:

        if transaction["type"] == "Deposit":

            deposits += 1
            deposit_amount += transaction["amount"]

        elif transaction["type"] == "Withdraw":

            withdrawals += 1
            withdraw_amount += transaction["amount"]

        elif transaction["type"] == "Transfer":

            transfers += 1
            transfer_amount += transaction["amount"]

    print("\n========== TRANSACTION STATISTICS ==========\n")

    print(f"Total Transactions : {len(transactions)}")

    print(f"Deposits           : {deposits}")
    print(f"Deposit Amount     : ₹{deposit_amount:.2f}")

    print(f"\nWithdrawals        : {withdrawals}")
    print(f"Withdrawal Amount  : ₹{withdraw_amount:.2f}")

    print(f"\nTransfers          : {transfers}")
    print(f"Transfer Amount    : ₹{transfer_amount:.2f}")


# ==========================================
# Print Transaction Receipt
# ==========================================

def print_transaction_receipt():

    transactions = get_transactions()

    transaction_id = input(
        "\nEnter Transaction ID : "
    ).strip()

    for transaction in transactions:

        if transaction["transaction_id"] == transaction_id:

            print("\n")
            print("=" * 45)
            print("             BANK RECEIPT")
            print("=" * 45)

            print("Transaction ID :", transaction["transaction_id"])
            print("Account Number :", transaction["account_number"])
            print("Transaction    :", transaction["type"])
            print("Amount         : ₹", transaction["amount"])
            print("Balance        : ₹", transaction["balance"])

            if transaction.get("receiver_account"):

                print(
                    "Receiver       :",
                    transaction["receiver_account"]
                )

            print("Date           :", transaction["date"])

            print("=" * 45)

            return

    print("Transaction Not Found.")


# ==========================================
# Highest Transaction
# ==========================================

def highest_transaction():

    transactions = get_transactions()

    if len(transactions) == 0:

        print("\nNo Transactions Found.")

        return

    highest = max(
        transactions,
        key=lambda x: x["amount"]
    )

    print("\n========== HIGHEST TRANSACTION ==========\n")

    print("Transaction ID :", highest["transaction_id"])
    print("Account Number :", highest["account_number"])
    print("Type           :", highest["type"])
    print("Amount         : ₹", highest["amount"])
    print("Date           :", highest["date"])


# ==========================================
# Bank Transaction Summary
# ==========================================

def bank_transaction_summary():

    transactions = get_transactions()

    total = 0

    for transaction in transactions:

        total += transaction["amount"]

    print("\n========== BANK SUMMARY ==========\n")

    print("Total Transactions :", len(transactions))
    print("Total Amount       : ₹", round(total, 2))


# ==========================================
# Transaction Menu
# ==========================================

def transaction_menu():

    while True:

        print("\n")
        print("=" * 50)
        print("        TRANSACTION MENU")
        print("=" * 50)

        print("1. View Transactions")
        print("2. Search Transaction")
        print("3. Transaction History")
        print("4. Mini Statement")
        print("5. Account Summary")
        print("6. Daily Transactions")
        print("7. Monthly Transactions")
        print("8. Transaction Statistics")
        print("9. Print Receipt")
        print("10. Highest Transaction")
        print("11. Bank Summary")
        print("12. Exit")

        choice = input("\nEnter Choice : ")

        if choice == "1":

            view_transactions()

        elif choice == "2":

            search_transaction()

        elif choice == "3":

            transaction_history()

        elif choice == "4":

            mini_statement()

        elif choice == "5":

            account_transaction_summary()

        elif choice == "6":

            daily_transactions()

        elif choice == "7":

            monthly_transactions()

        elif choice == "8":

            transaction_statistics()

        elif choice == "9":

            print_transaction_receipt()

        elif choice == "10":

            highest_transaction()

        elif choice == "11":

            bank_transaction_summary()

        elif choice == "12":

            print("\nReturning to Previous Menu...")

            break

        else:

            print("\nInvalid Choice.")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    transaction_menu()