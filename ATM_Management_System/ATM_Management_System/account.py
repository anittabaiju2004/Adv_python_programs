# Account operations
# account.py

from database import (
    get_customers,
    save_customers,
    get_transactions,
    save_transactions
)

from utils import (
    generate_account_number,
    generate_transaction_id,
    hash_pin,
    verify_pin,
    current_date,
    current_datetime,
    is_valid_phone,
    is_valid_email,
    is_valid_pin,
    is_valid_amount,
    print_receipt,
    find_customer
)


# ==========================================
# Register Account
# ==========================================

def register_account():

    customers = get_customers()

    print("\n========== REGISTER ACCOUNT ==========\n")

    name = input("Customer Name : ").strip()

    try:
        age = int(input("Age : "))
    except ValueError:
        print("Invalid Age.")
        return

    gender = input("Gender : ").strip()

    phone = input("Phone : ").strip()

    if not is_valid_phone(phone):
        print("Invalid Phone Number.")
        return

    email = input("Email : ").strip()

    if not is_valid_email(email):
        print("Invalid Email.")
        return

    address = input("Address : ").strip()

    pin = input("Create 4-Digit PIN : ").strip()

    if not is_valid_pin(pin):
        print("PIN must contain exactly 4 digits.")
        return

    for customer in customers:

        if customer["phone"] == phone:
            print("Phone Number Already Exists.")
            return

        if customer["email"] == email:
            print("Email Already Exists.")
            return

    account_number = generate_account_number(customers)

    customer = {

        "account_number": account_number,
        "name": name,
        "age": age,
        "gender": gender,
        "phone": phone,
        "email": email,
        "address": address,
        "pin": hash_pin(pin),
        "balance": 0.0,
        "status": "Active",
        "created_date": current_date()

    }

    customers.append(customer)

    save_customers(customers)

    print("\nAccount Created Successfully.")

    print("Account Number :", account_number)


# ==========================================
# Customer Login
# ==========================================

def customer_login():

    customers = get_customers()

    print("\n========== CUSTOMER LOGIN ==========\n")

    account_number = input("Account Number : ").strip()

    customer = find_customer(customers, account_number)

    if customer is None:

        print("Account Not Found.")

        return None

    if customer["status"] != "Active":

        print("This Account Is Frozen.")

        return None

    pin = input("PIN : ").strip()

    if not verify_pin(pin, customer["pin"]):

        print("Incorrect PIN.")

        return None

    print("\nLogin Successful.")

    print(f"Welcome {customer['name']}")

    return customer


# ==========================================
# Deposit Money
# ==========================================

def deposit_money():

    customers = get_customers()

    transactions = get_transactions()

    account_number = input("Enter Account Number : ")

    customer = find_customer(customers, account_number)

    if customer is None:

        print("Account Not Found.")

        return

    if customer["status"] != "Active":

        print("Account Frozen.")

        return

    amount = input("Deposit Amount : ")

    if not is_valid_amount(amount):

        print("Invalid Amount.")

        return

    amount = float(amount)

    customer["balance"] += amount

    transaction = {

        "transaction_id": generate_transaction_id(),
        "account_number": account_number,
        "type": "Deposit",
        "amount": amount,
        "date": current_datetime()

    }

    transactions.append(transaction)

    save_customers(customers)

    save_transactions(transactions)

    print("\nDeposit Successful.")

    print_receipt(
        account_number,
        "Deposit",
        amount,
        customer["balance"]
    )


# ==========================================
# Withdraw Money
# ==========================================

def withdraw_money():

    customers = get_customers()

    transactions = get_transactions()

    account_number = input("Enter Account Number : ")

    customer = find_customer(customers, account_number)

    if customer is None:

        print("Account Not Found.")

        return

    if customer["status"] != "Active":

        print("Account Frozen.")

        return

    pin = input("Enter PIN : ")

    if not verify_pin(pin, customer["pin"]):

        print("Incorrect PIN.")

        return

    amount = input("Withdraw Amount : ")

    if not is_valid_amount(amount):

        print("Invalid Amount.")

        return

    amount = float(amount)

    if amount > customer["balance"]:

        print("Insufficient Balance.")

        return

    customer["balance"] -= amount

    transaction = {

        "transaction_id": generate_transaction_id(),
        "account_number": account_number,
        "type": "Withdraw",
        "amount": amount,
        "date": current_datetime()

    }

    transactions.append(transaction)

    save_customers(customers)

    save_transactions(transactions)

    print("\nWithdrawal Successful.")

    print_receipt(
        account_number,
        "Withdraw",
        amount,
        customer["balance"]
    )
# ==========================================
# Transfer Money
# ==========================================

def transfer_money():

    customers = get_customers()
    transactions = get_transactions()

    print("\n========== FUND TRANSFER ==========\n")

    sender_acc = input("Sender Account Number : ")

    sender = find_customer(customers, sender_acc)

    if sender is None:
        print("Sender Account Not Found.")
        return

    if sender["status"] != "Active":
        print("Sender Account is Frozen.")
        return

    receiver_acc = input("Receiver Account Number : ")

    receiver = find_customer(customers, receiver_acc)

    if receiver is None:
        print("Receiver Account Not Found.")
        return

    if receiver["status"] != "Active":
        print("Receiver Account is Frozen.")
        return

    if sender_acc == receiver_acc:
        print("Cannot Transfer to Same Account.")
        return

    pin = input("Enter Your PIN : ")

    if not verify_pin(pin, sender["pin"]):
        print("Incorrect PIN.")
        return

    amount = input("Transfer Amount : ")

    if not is_valid_amount(amount):
        print("Invalid Amount.")
        return

    amount = float(amount)

    if amount > sender["balance"]:
        print("Insufficient Balance.")
        return

    sender["balance"] -= amount
    receiver["balance"] += amount

    transaction = {
        "transaction_id": generate_transaction_id(),
        "account_number": sender_acc,
        "receiver_account": receiver_acc,
        "type": "Transfer",
        "amount": amount,
        "date": current_datetime()
    }

    transactions.append(transaction)

    save_customers(customers)
    save_transactions(transactions)

    print("\nTransfer Successful.")

    print_receipt(
        sender_acc,
        "Transfer",
        amount,
        sender["balance"]
    )


# ==========================================
# Balance Inquiry
# ==========================================

def balance_inquiry():

    customers = get_customers()

    print("\n========== BALANCE INQUIRY ==========\n")

    account_number = input("Account Number : ")

    customer = find_customer(customers, account_number)

    if customer is None:
        print("Account Not Found.")
        return

    pin = input("Enter PIN : ")

    if not verify_pin(pin, customer["pin"]):
        print("Incorrect PIN.")
        return

    print("\n========== ACCOUNT DETAILS ==========")

    print(f"Account Number : {customer['account_number']}")
    print(f"Customer Name  : {customer['name']}")
    print(f"Balance        : ₹{customer['balance']:.2f}")


# ==========================================
# Transaction History
# ==========================================

def transaction_history():

    transactions = get_transactions()

    account_number = input("Enter Account Number : ")

    records = []

    for transaction in transactions:

        if transaction["account_number"] == account_number:
            records.append(transaction)

    if len(records) == 0:
        print("\nNo Transaction History Found.")
        return

    print("\n========== TRANSACTION HISTORY ==========")

    for transaction in records:

        print("-" * 60)

        print("Transaction ID :", transaction["transaction_id"])
        print("Type           :", transaction["type"])
        print("Amount         : ₹", transaction["amount"])

        if transaction["type"] == "Transfer":
            print("Receiver       :", transaction["receiver_account"])

        print("Date           :", transaction["date"])


# ==========================================
# Mini Statement
# ==========================================

def mini_statement():

    transactions = get_transactions()

    account_number = input("Enter Account Number : ")

    records = []

    for transaction in transactions:

        if transaction["account_number"] == account_number:
            records.append(transaction)

    if len(records) == 0:
        print("\nNo Transactions Available.")
        return

    print("\n========== MINI STATEMENT ==========")

    recent_transactions = records[-5:]

    for transaction in recent_transactions:

        print("-" * 50)

        print(f"ID     : {transaction['transaction_id']}")
        print(f"Type   : {transaction['type']}")
        print(f"Amount : ₹{transaction['amount']}")
        print(f"Date   : {transaction['date']}")

        if transaction["type"] == "Transfer":
            print(f"To     : {transaction['receiver_account']}")

    print("-" * 50)
    print(f"Total Transactions : {len(records)}")

from database import (
    get_fixed_deposits,
    save_fixed_deposits
)

from utils import generate_fd_id


# ==========================================
# Change PIN
# ==========================================

def change_pin():

    customers = get_customers()

    print("\n========== CHANGE PIN ==========\n")

    account_number = input("Account Number : ")

    customer = find_customer(customers, account_number)

    if customer is None:
        print("Account Not Found.")
        return

    old_pin = input("Current PIN : ")

    if not verify_pin(old_pin, customer["pin"]):
        print("Incorrect PIN.")
        return

    new_pin = input("New 4-Digit PIN : ")

    if not is_valid_pin(new_pin):
        print("PIN must contain exactly 4 digits.")
        return

    confirm_pin = input("Confirm PIN : ")

    if new_pin != confirm_pin:
        print("PIN does not match.")
        return

    customer["pin"] = hash_pin(new_pin)

    save_customers(customers)

    print("\nPIN Changed Successfully.")


# ==========================================
# Interest Calculator
# ==========================================

def interest_calculator():

    print("\n========== INTEREST CALCULATOR ==========\n")

    try:
        principal = float(input("Principal Amount : ₹"))
        rate = float(input("Interest Rate (%) : "))
        years = float(input("Duration (Years) : "))
    except ValueError:
        print("Invalid Input.")
        return

    interest = (principal * rate * years) / 100

    maturity = principal + interest

    print("\n========== RESULT ==========")
    print(f"Principal Amount : ₹{principal:.2f}")
    print(f"Interest         : ₹{interest:.2f}")
    print(f"Maturity Amount  : ₹{maturity:.2f}")


# ==========================================
# Create Fixed Deposit
# ==========================================

def create_fixed_deposit():

    customers = get_customers()
    fd_list = get_fixed_deposits()

    print("\n========== FIXED DEPOSIT ==========\n")

    account_number = input("Account Number : ")

    customer = find_customer(customers, account_number)

    if customer is None:
        print("Account Not Found.")
        return

    pin = input("PIN : ")

    if not verify_pin(pin, customer["pin"]):
        print("Incorrect PIN.")
        return

    try:
        amount = float(input("Deposit Amount : ₹"))
    except ValueError:
        print("Invalid Amount.")
        return

    if amount > customer["balance"]:
        print("Insufficient Balance.")
        return

    try:
        years = int(input("Duration (Years) : "))
    except ValueError:
        print("Invalid Duration.")
        return

    rate = 6.5

    interest = (amount * rate * years) / 100

    maturity = amount + interest

    customer["balance"] -= amount

    fd = {

        "fd_id": generate_fd_id(),
        "account_number": account_number,
        "amount": amount,
        "interest_rate": rate,
        "duration": years,
        "interest": interest,
        "maturity_amount": maturity,
        "status": "Active",
        "created_date": current_date()

    }

    fd_list.append(fd)

    save_customers(customers)
    save_fixed_deposits(fd_list)

    print("\nFixed Deposit Created Successfully.")
    print("FD Number :", fd["fd_id"])


# ==========================================
# View Fixed Deposits
# ==========================================

def view_fixed_deposits():

    fd_list = get_fixed_deposits()

    account_number = input("Account Number : ")

    found = False

    print("\n========== FIXED DEPOSITS ==========")

    for fd in fd_list:

        if fd["account_number"] == account_number:

            found = True

            print("-" * 60)
            print("FD Number        :", fd["fd_id"])
            print("Amount           : ₹", fd["amount"])
            print("Interest Rate    :", fd["interest_rate"], "%")
            print("Duration         :", fd["duration"], "Years")
            print("Interest         : ₹", fd["interest"])
            print("Maturity Amount  : ₹", fd["maturity_amount"])
            print("Status           :", fd["status"])

    if not found:
        print("No Fixed Deposits Found.")


# ==========================================
# Close Fixed Deposit
# ==========================================

def close_fixed_deposit():

    customers = get_customers()
    fd_list = get_fixed_deposits()

    fd_number = input("Enter FD Number : ")

    for fd in fd_list:

        if fd["fd_id"] == fd_number:

            if fd["status"] == "Closed":
                print("FD Already Closed.")
                return

            customer = find_customer(
                customers,
                fd["account_number"]
            )

            customer["balance"] += fd["maturity_amount"]

            fd["status"] = "Closed"

            save_customers(customers)
            save_fixed_deposits(fd_list)

            print("\nFixed Deposit Closed Successfully.")
            print(
                f"₹{fd['maturity_amount']} credited to your account."
            )

            return

    print("FD Not Found.")
from database import (
    get_loans,
    save_loans
)

from utils import generate_loan_id


# ==========================================
# Apply Loan
# ==========================================

def apply_loan():

    customers = get_customers()
    loans = get_loans()

    print("\n========== APPLY LOAN ==========\n")

    account_number = input("Account Number : ")

    customer = find_customer(customers, account_number)

    if customer is None:
        print("Account Not Found.")
        return

    pin = input("PIN : ")

    if not verify_pin(pin, customer["pin"]):
        print("Incorrect PIN.")
        return

    print("\nLoan Types")
    print("1. Personal Loan")
    print("2. Home Loan")
    print("3. Car Loan")
    print("4. Education Loan")

    choice = input("Select Loan Type : ")

    loan_types = {
        "1": "Personal Loan",
        "2": "Home Loan",
        "3": "Car Loan",
        "4": "Education Loan"
    }

    if choice not in loan_types:
        print("Invalid Choice.")
        return

    try:
        amount = float(input("Loan Amount : ₹"))
        years = int(input("Duration (Years) : "))
    except:
        print("Invalid Input.")
        return

    rate = 10

    interest = (amount * rate * years) / 100

    total = amount + interest

    loan = {

        "loan_id": generate_loan_id(),
        "account_number": account_number,
        "loan_type": loan_types[choice],
        "loan_amount": amount,
        "interest_rate": rate,
        "duration": years,
        "total_payable": total,
        "remaining_amount": total,
        "status": "Active",
        "created_date": current_date()

    }

    loans.append(loan)

    customer["balance"] += amount

    save_customers(customers)
    save_loans(loans)

    print("\nLoan Approved Successfully.")

    print("Loan Number :", loan["loan_id"])


# ==========================================
# View Loans
# ==========================================

def view_loans():

    loans = get_loans()

    account_number = input("Account Number : ")

    found = False

    print("\n========== LOANS ==========")

    for loan in loans:

        if loan["account_number"] == account_number:

            found = True

            print("-" * 60)
            print("Loan Number :", loan["loan_id"])
            print("Loan Type   :", loan["loan_type"])
            print("Loan Amount : ₹", loan["loan_amount"])
            print("Remaining   : ₹", loan["remaining_amount"])
            print("Status      :", loan["status"])

    if not found:
        print("No Loans Found.")


# ==========================================
# Repay Loan
# ==========================================

def repay_loan():

    customers = get_customers()
    loans = get_loans()

    loan_number = input("Loan Number : ")

    for loan in loans:

        if loan["loan_id"] == loan_number:

            customer = find_customer(
                customers,
                loan["account_number"]
            )

            try:
                amount = float(
                    input("Repayment Amount : ₹")
                )
            except:
                print("Invalid Amount.")
                return

            if amount > customer["balance"]:
                print("Insufficient Balance.")
                return

            customer["balance"] -= amount

            loan["remaining_amount"] -= amount

            if loan["remaining_amount"] <= 0:

                loan["remaining_amount"] = 0
                loan["status"] = "Closed"

            save_customers(customers)
            save_loans(loans)

            print("\nLoan Payment Successful.")

            return

    print("Loan Not Found.")


# ==========================================
# Customer Dashboard
# ==========================================

def customer_dashboard():

    while True:

        print("\n")
        print("=" * 50)
        print("        CUSTOMER DASHBOARD")
        print("=" * 50)

        print("1. Deposit Money")
        print("2. Withdraw Money")
        print("3. Transfer Money")
        print("4. Balance Inquiry")
        print("5. Transaction History")
        print("6. Mini Statement")
        print("7. Change PIN")
        print("8. Interest Calculator")
        print("9. Fixed Deposit")
        print("10. View Fixed Deposits")
        print("11. Close Fixed Deposit")
        print("12. Apply Loan")
        print("13. View Loans")
        print("14. Repay Loan")
        print("15. Logout")

        choice = input("\nEnter Choice : ")

        if choice == "1":
            deposit_money()

        elif choice == "2":
            withdraw_money()

        elif choice == "3":
            transfer_money()

        elif choice == "4":
            balance_inquiry()

        elif choice == "5":
            transaction_history()

        elif choice == "6":
            mini_statement()

        elif choice == "7":
            change_pin()

        elif choice == "8":
            interest_calculator()

        elif choice == "9":
            create_fixed_deposit()

        elif choice == "10":
            view_fixed_deposits()

        elif choice == "11":
            close_fixed_deposit()

        elif choice == "12":
            apply_loan()

        elif choice == "13":
            view_loans()

        elif choice == "14":
            repay_loan()

        elif choice == "15":

            logout()

            break

        else:

            print("Invalid Choice.")


# ==========================================
# Logout
# ==========================================

def logout():

    print("\nLogged Out Successfully.")