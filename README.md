# Multi-Account Finance Tracker

A simple, multi-account personal finance tracking application built with Python, Tkinter, and ttkbootstrap. It allows you to manage multiple accounts (like Cash, Bank, E-wallet), track income and expenses, and transfer funds between them. Data is saved locally in a JSON file.

## Features

*   **Multi-Account Management:** Add, delete, and manage multiple financial accounts.
*   **Transaction Logging:** Record income and expense transactions with date, account, description (optional), amount, and type.
*   **Fund Transfers:** Easily transfer funds between your different accounts.
*   **Balance Overview:** View the current balance for each account and the total combined balance.
*   **Transaction History:** Displays all transactions in a sortable list view.
*   **Insufficient Funds Check:** Prevents adding expenses or making transfers that would result in a negative balance for an account.
*   **Data Persistence:** Automatically saves and loads your accounts and transactions to/from a local `finance_data.json` file.
*   **Transaction Deletion:** Remove incorrect or unwanted transactions (warns if deleting part of a transfer).
*   **Themed Interface:** Uses `ttkbootstrap` for a modern look and feel (defaults to 'darkly' theme).

## Requirements

*   Python 3.x
*   `ttkbootstrap` library

## Installation

1.  **Clone the repository or download the source code.**
2.  **Install the required library:**
    Open your terminal or command prompt and run:
    ```bash
    pip install ttkbootstrap
    ```

## Usage

1.  Navigate to the directory where you saved the script in your terminal.
2.  Run the application using Python:
    ```bash
    python finance_tracker.py
    ```

3.  **Getting Started:**
    *   Use the "Manage Accounts" section to add your initial accounts (e.g., "Cash", "Bank Account", "Credit Card").
    *   Use the "Add Transaction" section to log your income and expenses, selecting the appropriate account.
    *   Use the "Transfer Funds" section to move money between your accounts.
    *   View your balances and transaction history in the right-hand panel.
    *   Select a transaction in the list and click "Delete Selected Transaction" to remove it.

## Data Storage

*   All account names and transaction data are stored locally in a file named `finance_data.json` in the same directory as the script.
*   This file is created automatically when you first run the application and save data (or on closing if you confirm saving).
*   **Important:** Back up this `finance_data.json` file regularly if you rely on this application, as it contains all your financial data entered into the app.

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
