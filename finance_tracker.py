import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from ttkbootstrap.widgets import DateEntry
import json
from datetime import datetime # Keep datetime
import os
from collections import defaultdict

# --- Plotting Imports --- (REMOVED)
# import matplotlib.pyplot as plt
# from matplotlib.figure import Figure
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# import pandas as pd
# import matplotlib.dates as mdates
# plt.style.use('ggplot')

# --- Configuration ---
FINANCE_DATA_FILE = "finance_data.json"
DEFAULT_THEME = "darkly"
CURRENCY_SYMBOL = "₱"
TRANS_EXPENSE = "Expense"
TRANS_INCOME = "Income"
TRANSFER_OUT_DESC = "Transfer to {}"
TRANSFER_IN_DESC = "Transfer from {}"


# --- Main Application Class ---
class FinanceTrackerApp:
    def __init__(self, window):
        self.window = window
        self.window.title("Multi-Account Finance Tracker")
        # self.window.geometry("900x700") # Adjust size as needed

        self.style = tb.Style(theme=DEFAULT_THEME)
        self.window.configure(background=self.style.colors.bg)

        self.accounts = []
        self.transactions = []
        self.load_data()

        # --- Data Variables (Tkinter) ---
        # (These remain the same)
        self.date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.description_var = tk.StringVar()
        self.amount_var = tk.DoubleVar(value=0.0)
        self.type_var = tk.StringVar(value=TRANS_EXPENSE)
        self.transaction_account_var = tk.StringVar()
        self.new_account_name_var = tk.StringVar()
        self.delete_account_var = tk.StringVar()
        self.transfer_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.transfer_amount_var = tk.DoubleVar(value=0.0)
        self.transfer_from_account_var = tk.StringVar()
        self.transfer_to_account_var = tk.StringVar()
        self.total_balance_var = tk.StringVar(value=f"Total Balance: {CURRENCY_SYMBOL}0.00")
        self.account_balance_labels = {}

        # --- Plotting Variables --- (REMOVED)
        # self.pie_fig = None
        # self.pie_ax = None
        # self.pie_canvas = None
        # self.line_fig = None
        # self.line_ax = None
        # self.line_canvas = None
        # self.line_period_var = tk.StringVar(value="Month")

        # --- Build UI and Set Initial State ---
        self.create_widgets()           # Create all UI elements
        self.update_account_comboboxes()# Populate comboboxes
        self.update_transaction_list()  # Populate treeview
        self.update_balances()          # Calculate/display balances

        # --- Window Closing Behavior ---
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- create_widgets Restored ---
    def create_widgets(self):
        """Creates the main widgets without the notebook."""
        main_frame = tb.Frame(self.window, padding=15)
        main_frame.pack(fill=BOTH, expand=True)

        left_panel = tb.Frame(main_frame, padding=(0, 0, 10, 0))
        left_panel.pack(side=LEFT, fill=Y, padx=(0, 10))

        right_panel = tb.Frame(main_frame)
        right_panel.pack(side=LEFT, fill=BOTH, expand=True)

        # --- Input Frame (Moved back from create_tab1_widgets) ---
        input_frame = tb.LabelFrame(left_panel, text="Add Transaction", padding=10, bootstyle=SECONDARY)
        input_frame.pack(fill=X, pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)

        tb.Label(input_frame, text="Date:").grid(row=0, column=0, padx=5, pady=3, sticky=W)
        self.date_entry = DateEntry(input_frame, bootstyle=PRIMARY, firstweekday=0, dateformat='%Y-%m-%d')
        self.date_entry.grid(row=0, column=1, padx=5, pady=3, sticky=EW)
        self.date_entry.entry.config(textvariable=self.date_var)

        tb.Label(input_frame, text="Account:").grid(row=1, column=0, padx=5, pady=3, sticky=W)
        self.transaction_account_combo = tb.Combobox(input_frame, textvariable=self.transaction_account_var, state="readonly", bootstyle=PRIMARY)
        self.transaction_account_combo.grid(row=1, column=1, padx=5, pady=3, sticky=EW)
        ToolTip(self.transaction_account_combo, text="Select the account for this transaction", bootstyle=(INFO, INVERSE))

        tb.Label(input_frame, text="Description:").grid(row=2, column=0, padx=5, pady=3, sticky=W)
        self.desc_entry = tb.Entry(input_frame, textvariable=self.description_var, bootstyle=PRIMARY)
        self.desc_entry.grid(row=2, column=1, padx=5, pady=3, sticky=EW)
        ToolTip(self.desc_entry, text="Description (e.g., Groceries, Salary) - Optional", bootstyle=(INFO, INVERSE))

        tb.Label(input_frame, text="Amount:").grid(row=3, column=0, padx=5, pady=3, sticky=W)
        self.amount_entry = tb.Entry(input_frame, textvariable=self.amount_var, bootstyle=PRIMARY)
        self.amount_entry.grid(row=3, column=1, padx=5, pady=3, sticky=EW)
        ToolTip(self.amount_entry, text="Amount (positive number)", bootstyle=(INFO, INVERSE))

        tb.Label(input_frame, text="Type:").grid(row=4, column=0, padx=5, pady=3, sticky=W)
        self.type_combobox = tb.Combobox(input_frame, textvariable=self.type_var, values=[TRANS_EXPENSE, TRANS_INCOME], state="readonly", bootstyle=PRIMARY)
        self.type_combobox.grid(row=4, column=1, padx=5, pady=3, sticky=EW)

        self.add_button = tb.Button(input_frame, text="Add Transaction", command=self.add_transaction, bootstyle=SUCCESS)
        self.add_button.grid(row=5, column=0, columnspan=2, pady=8, sticky=EW)

        # --- Account Management Frame (Moved back from create_tab1_widgets) ---
        account_mgmt_frame = tb.LabelFrame(left_panel, text="Manage Accounts", padding=10, bootstyle=SECONDARY)
        account_mgmt_frame.pack(fill=X, pady=(0, 10))
        account_mgmt_frame.columnconfigure(1, weight=1)

        tb.Label(account_mgmt_frame, text="New Name:").grid(row=0, column=0, padx=5, pady=(5,2), sticky=W)
        self.new_account_entry = tb.Entry(account_mgmt_frame, textvariable=self.new_account_name_var, bootstyle=PRIMARY)
        self.new_account_entry.grid(row=0, column=1, padx=5, pady=(5,2), sticky=EW)
        ToolTip(self.new_account_entry, text="Enter name for a new account (e.g., Bank B)", bootstyle=(INFO, INVERSE))
        self.add_account_button = tb.Button(account_mgmt_frame, text="Add", command=self.add_account, bootstyle=INFO)
        self.add_account_button.grid(row=0, column=2, padx=5, pady=(5,2))

        ttk.Separator(account_mgmt_frame, orient=HORIZONTAL).grid(row=1, column=0, columnspan=3, sticky='ew', pady=8)

        tb.Label(account_mgmt_frame, text="Delete Acct:").grid(row=2, column=0, padx=5, pady=(2,5), sticky=W)
        self.delete_account_combo = tb.Combobox(account_mgmt_frame, textvariable=self.delete_account_var, state="readonly", bootstyle=PRIMARY)
        self.delete_account_combo.grid(row=2, column=1, padx=5, pady=(2,5), sticky=EW)
        ToolTip(self.delete_account_combo, text="Select account to delete (must have no transactions)", bootstyle=(INFO, INVERSE))
        self.delete_account_button = tb.Button(account_mgmt_frame, text="Delete", command=self.delete_account, bootstyle=DANGER)
        self.delete_account_button.grid(row=2, column=2, padx=5, pady=(2,5))

        # --- Transfer Funds Frame (Moved back from create_tab1_widgets) ---
        transfer_frame = tb.LabelFrame(left_panel, text="Transfer Funds", padding=10, bootstyle=SECONDARY)
        transfer_frame.pack(fill=X, pady=(0, 10))
        transfer_frame.columnconfigure(1, weight=1)

        tb.Label(transfer_frame, text="Date:").grid(row=0, column=0, padx=5, pady=3, sticky=W)
        self.transfer_date_entry = DateEntry(transfer_frame, bootstyle=PRIMARY, firstweekday=0, dateformat='%Y-%m-%d')
        self.transfer_date_entry.grid(row=0, column=1, padx=5, pady=3, sticky=EW)
        self.transfer_date_entry.entry.config(textvariable=self.transfer_date_var)

        tb.Label(transfer_frame, text="From Account:").grid(row=1, column=0, padx=5, pady=3, sticky=W)
        self.transfer_from_combo = tb.Combobox(transfer_frame, textvariable=self.transfer_from_account_var, state="readonly", bootstyle=PRIMARY)
        self.transfer_from_combo.grid(row=1, column=1, padx=5, pady=3, sticky=EW)

        tb.Label(transfer_frame, text="To Account:").grid(row=2, column=0, padx=5, pady=3, sticky=W)
        self.transfer_to_combo = tb.Combobox(transfer_frame, textvariable=self.transfer_to_account_var, state="readonly", bootstyle=PRIMARY)
        self.transfer_to_combo.grid(row=2, column=1, padx=5, pady=3, sticky=EW)

        tb.Label(transfer_frame, text="Amount:").grid(row=3, column=0, padx=5, pady=3, sticky=W)
        self.transfer_amount_entry = tb.Entry(transfer_frame, textvariable=self.transfer_amount_var, bootstyle=PRIMARY)
        self.transfer_amount_entry.grid(row=3, column=1, padx=5, pady=3, sticky=EW)
        ToolTip(self.transfer_amount_entry, text="Amount to transfer", bootstyle=(INFO, INVERSE))

        self.transfer_button = tb.Button(transfer_frame, text="Transfer Funds", command=self.transfer_funds, bootstyle=WARNING)
        self.transfer_button.grid(row=4, column=0, columnspan=2, pady=8, sticky=EW)

        # --- Transaction List Frame (Moved back from create_tab1_widgets) ---
        list_frame = tb.LabelFrame(right_panel, text="Transactions", padding=10, bootstyle=SECONDARY)
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        columns = ("date", "account", "description", "type", "amount")
        self.tree = tb.Treeview(list_frame, columns=columns, show='headings', bootstyle=PRIMARY)

        self.tree.heading("date", text="Date"); self.tree.heading("account", text="Account"); self.tree.heading("description", text="Description"); self.tree.heading("type", text="Type"); self.tree.heading("amount", text="Amount")
        self.tree.column("date", width=90, anchor=CENTER); self.tree.column("account", width=100, anchor=W); self.tree.column("description", width=200, anchor=W); self.tree.column("type", width=80, anchor=CENTER); self.tree.column("amount", width=100, anchor=E)

        tree_scrollbar = tb.Scrollbar(list_frame, orient=VERTICAL, command=self.tree.yview, bootstyle=ROUND)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.pack(side=RIGHT, fill=Y)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)

        try: # Tag configuration (as before)
            dark_row_color = self.style.colors.get('dark') or "#303030"; bg_color = self.style.colors.bg or "#343a40"
            if dark_row_color == bg_color: dark_row_color = self.style.colors.inputbg or "#404040"
            self.tree.tag_configure('oddrow', background=dark_row_color); self.tree.tag_configure('evenrow', background=bg_color)
            self.tree.tag_configure('income', foreground=self.style.colors.success); self.tree.tag_configure('expense', foreground=self.style.colors.danger)
        except Exception as e:
            print(f"Warning: Could not configure treeview colors: {e}"); self.tree.tag_configure('oddrow', background='#333333'); self.tree.tag_configure('evenrow', background='#272727'); self.tree.tag_configure('income', foreground='green'); self.tree.tag_configure('expense', foreground='red')

        # --- Balances Frame (Moved back from create_tab1_widgets) ---
        balances_frame = tb.LabelFrame(right_panel, text="Account Balances", padding=10, bootstyle=SECONDARY)
        balances_frame.pack(fill=X, pady=(0, 5))

        self.account_balances_display_frame = tb.Frame(balances_frame)
        self.account_balances_display_frame.pack(fill=X, pady=(0, 5))
        self.total_balance_label = tb.Label(balances_frame, textvariable=self.total_balance_var, font=("Helvetica", 14, "bold"), anchor=E, bootstyle=PRIMARY)
        self.total_balance_label.pack(fill=X, padx=5, pady=(5, 0))

        # --- Bottom Bar (Moved back from create_tab1_widgets) ---
        bottom_bar = tb.Frame(right_panel)
        bottom_bar.pack(fill=X, pady=(5,0))

        self.delete_transaction_button = tb.Button(bottom_bar, text="Delete Selected Transaction", command=self.delete_selected_transaction, bootstyle=(DANGER, OUTLINE))
        self.delete_transaction_button.pack(side=LEFT, padx=5)
        ToolTip(self.delete_transaction_button, text="Select a transaction in the list above and click here to delete it.", bootstyle=(INFO, INVERSE))

    # --- Plotting Methods Removed ---
    # def create_tab1_widgets(self, parent_frame): ... (DELETED)
    # def create_tab2_widgets(self, parent_frame): ... (DELETED)
    # def create_tab3_widgets(self, parent_frame): ... (DELETED)
    # def update_pie_chart(self): ... (DELETED)
    # def update_line_graph(self): ... (DELETED)

    # --- update_balances Cleaned ---
    def update_balances(self):
        """Calculates and updates all balance displays (PLOTS REMOVED)."""
        account_balances, total_balance = self.calculate_balances()
        # (Balance label updates remain the same)
        total_balance_color = SUCCESS if total_balance >= 0 else DANGER
        self.total_balance_label.config(bootstyle=total_balance_color)
        self.total_balance_var.set(f"Total Balance: {CURRENCY_SYMBOL}{total_balance:,.2f}")
        # (Account balance display loop remains the same)
        for widget in self.account_balances_display_frame.winfo_children(): widget.destroy()
        self.account_balance_labels.clear()
        col_count = 0; max_cols = 2; row_num = 0
        for account_name in sorted(self.accounts):
            balance = account_balances.get(account_name, 0.0)
            balance_color = SUCCESS if balance >= 0 else DANGER
            label_text = f"{account_name}: {CURRENCY_SYMBOL}{balance:,.2f}"
            label = tb.Label(self.account_balances_display_frame, text=label_text, bootstyle=balance_color)
            label.grid(row=row_num, column=col_count, padx=5, pady=2, sticky=W)
            self.account_balance_labels[account_name] = label
            col_count += 1
            if col_count >= max_cols: col_count = 0; row_num += 1
        if not self.accounts:
             no_accounts_label = tb.Label(self.account_balances_display_frame, text="No accounts added yet.", bootstyle=SECONDARY)
             no_accounts_label.grid(row=0, column=0, padx=5, pady=2, sticky=W)

        # --- Trigger Plot Updates --- (REMOVED)
        # if hasattr(self, 'pie_canvas') and self.pie_canvas: ...
        # if hasattr(self, 'line_canvas') and self.line_canvas: ...

    # --- Account Management (Keep as is) ---
    def add_account(self):
        # ... (no changes needed) ...
        """Adds a new account to the list."""
        new_name = self.new_account_name_var.get().strip()
        if not new_name:
            messagebox.showwarning("Input Error", "Account name cannot be empty.", parent=self.window)
            return
        if new_name in self.accounts:
            messagebox.showwarning("Input Error", f"Account '{new_name}' already exists.", parent=self.window)
            return

        self.accounts.append(new_name)
        self.accounts.sort()
        self.update_account_comboboxes()
        self.update_balances()
        self.new_account_name_var.set("")
        # self.save_data()
        messagebox.showinfo("Success", f"Account '{new_name}' added.", parent=self.window)


    def delete_account(self):
        # ... (no changes needed) ...
        """Deletes the selected account if it has no transactions."""
        account_to_delete = self.delete_account_var.get()

        if not account_to_delete:
            messagebox.showwarning("Selection Error", "Please select an account to delete.", parent=self.window)
            return

        # --- Safety Check: Ensure account has no transactions ---
        has_transactions = False
        for trans in self.transactions:
            if trans.get('account') == account_to_delete:
                has_transactions = True
                break

        if has_transactions:
            messagebox.showerror("Deletion Prevented", f"Cannot delete account '{account_to_delete}' because it has existing transactions.\n\nPlease delete or reassign its transactions first.", parent=self.window)
            return
        # --- End Safety Check ---

        # Confirmation
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete the account '{account_to_delete}'?\n\nThis account currently has no transactions.", parent=self.window):
            try:
                self.accounts.remove(account_to_delete)
                self.update_account_comboboxes()
                self.update_balances()
                self.delete_account_var.set("") # Clear selection
                # self.save_data()
                messagebox.showinfo("Success", f"Account '{account_to_delete}' deleted.", parent=self.window)
            except ValueError:
                messagebox.showerror("Error", f"Account '{account_to_delete}' not found in the list (this shouldn't happen).", parent=self.window)
            except Exception as e:
                 messagebox.showerror("Error", f"An unexpected error occurred while deleting the account: {e}", parent=self.window)
                 print(f"Error deleting account: {e}")


    def update_account_comboboxes(self):
        # ... (no changes needed) ...
        """Updates the values in ALL account selection comboboxes."""
        account_list = list(self.accounts) # Create a copy
        # Update all comboboxes that list accounts
        self.transaction_account_combo['values'] = account_list
        self.transfer_from_combo['values'] = account_list
        self.transfer_to_combo['values'] = account_list
        self.delete_account_combo['values'] = account_list # <--- Update delete combo

        # Function to clear selection if current value is invalid
        def clear_if_invalid(combo_var, valid_list):
            if combo_var.get() not in valid_list:
                combo_var.set('')

        clear_if_invalid(self.transaction_account_var, account_list)
        clear_if_invalid(self.transfer_from_account_var, account_list)
        clear_if_invalid(self.transfer_to_account_var, account_list)
        clear_if_invalid(self.delete_account_var, account_list) # <--- Clear delete combo selection if needed


    # --- Transaction Handling (Keep as is) ---
    def add_transaction(self):
        # ... (no changes needed) ...
        """Adds a new income or expense transaction."""
        try:
            date_str = self.date_var.get()
            account = self.transaction_account_var.get()
            description = self.description_var.get().strip() # Description is now optional
            amount = self.amount_var.get()
            trans_type = self.type_var.get()

            # --- Basic Validation ---
            if not date_str:
                 messagebox.showerror("Input Error", "Please select a valid date.", parent=self.window)
                 return
            try: datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                 messagebox.showerror("Input Error", f"Invalid date format: '{date_str}'. Use YYYY-MM-DD.", parent=self.window)
                 return
            if not account:
                messagebox.showerror("Input Error", "Please select an account.", parent=self.window)
                return
            # Description check is removed as per previous request
            if amount <= 0:
                messagebox.showerror("Input Error", "Amount must be a positive number.", parent=self.window)
                return
            if not trans_type:
                messagebox.showerror("Input Error", "Please select a transaction type.", parent=self.window)
                return

            # --- Insufficient Funds Check ---
            if trans_type == TRANS_EXPENSE:
                account_balances, _ = self.calculate_balances()
                current_balance = account_balances.get(account, 0.0)
                if current_balance < amount:
                    messagebox.showerror(
                        "Insufficient Funds",
                        f"Cannot add expense of {CURRENCY_SYMBOL}{amount:,.2f}.\n"
                        f"Account '{account}' only has {CURRENCY_SYMBOL}{current_balance:,.2f}.",
                        parent=self.window
                    )
                    return # Stop processing
            # --- End Insufficient Funds Check ---

            transaction = {
                "date": date_str, "account": account, "description": description,
                "amount": amount, "type": trans_type, "id": datetime.now().timestamp()
            }
            self.transactions.append(transaction)
            self.update_transaction_list()
            self.update_balances()
            # self.save_data()

            self.description_var.set("")
            self.amount_var.set(0.0)
            self.desc_entry.focus_set()

        except ValueError:
            messagebox.showerror("Input Error", "Invalid amount entered. Please enter a number.", parent=self.window)
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=self.window)
            print(f"Error adding transaction: {e}")

    def transfer_funds(self):
        # ... (no changes needed) ...
        """Creates two transactions to represent a transfer between accounts."""
        try:
            date_str = self.transfer_date_var.get()
            from_account = self.transfer_from_account_var.get()
            to_account = self.transfer_to_account_var.get()
            amount = self.transfer_amount_var.get()

            # --- Validation ---
            if not date_str:
                 messagebox.showerror("Input Error", "Please select a valid date for the transfer.", parent=self.window); return
            try: datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                 messagebox.showerror("Input Error", f"Invalid date format: '{date_str}'. Use YYYY-MM-DD.", parent=self.window); return
            if not from_account or not to_account:
                 messagebox.showerror("Input Error", "Please select both 'From' and 'To' accounts.", parent=self.window); return
            if from_account == to_account:
                 messagebox.showerror("Input Error", "'From' and 'To' accounts cannot be the same.", parent=self.window); return
            if amount <= 0:
                 messagebox.showerror("Input Error", "Transfer amount must be positive.", parent=self.window); return

            # --- Insufficient Funds Check for Transfer Out ---
            account_balances, _ = self.calculate_balances()
            current_balance_from = account_balances.get(from_account, 0.0)
            if current_balance_from < amount:
                messagebox.showerror(
                    "Insufficient Funds",
                    f"Cannot transfer {CURRENCY_SYMBOL}{amount:,.2f}.\n"
                    f"Account '{from_account}' only has {CURRENCY_SYMBOL}{current_balance_from:,.2f}.",
                    parent=self.window
                )
                return # Stop processing the transfer
            # --- End Insufficient Funds Check ---


            transfer_time = datetime.now().timestamp()
            transfer_id_out = f"tf_out_{transfer_time}"
            transfer_id_in = f"tf_in_{transfer_time}"

            trans_out = {
                "date": date_str, "account": from_account,
                "description": TRANSFER_OUT_DESC.format(to_account),
                "amount": amount, "type": TRANS_EXPENSE, "id": transfer_id_out
            }
            trans_in = {
                "date": date_str, "account": to_account,
                "description": TRANSFER_IN_DESC.format(from_account),
                "amount": amount, "type": TRANS_INCOME, "id": transfer_id_in
            }
            self.transactions.append(trans_out)
            self.transactions.append(trans_in)
            self.update_transaction_list()
            self.update_balances()
            # self.save_data()

            self.transfer_amount_var.set(0.0)
            self.transfer_from_account_var.set("")
            self.transfer_to_account_var.set("")
            messagebox.showinfo("Success", f"Transferred {CURRENCY_SYMBOL}{amount:,.2f} from '{from_account}' to '{to_account}'.", parent=self.window)
        except ValueError:
            messagebox.showerror("Input Error", "Invalid transfer amount entered.", parent=self.window)
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during transfer: {e}", parent=self.window)
            print(f"Error transferring funds: {e}")


    def delete_selected_transaction(self):
        """Deletes the selected transaction from the list."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a transaction to delete.", parent=self.window)
            return
        selected_iid = selected_items[0]
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected transaction(s)?\n(Deleting one part of a transfer will require manually deleting the other)", parent=self.window):
            return

        try:
            item_details = self.tree.item(selected_iid)
            item_values = item_details['values']
            transaction_to_delete = None
            found_index = -1

            # Store expected values from the tree for comparison
            expected_date = str(item_values[0])
            expected_account = str(item_values[1])
            expected_desc = str(item_values[2])
            expected_type = str(item_values[3])
            expected_amount_str = str(item_values[4])

            # --- FIX: Prepare the amount from Treeview for comparison ---
            try:
                # Remove comma before converting the Treeview amount string
                expected_amount_float = float(expected_amount_str.replace(',', ''))
            except ValueError:
                 messagebox.showerror("Error", f"Could not parse amount '{expected_amount_str}' from selected row.", parent=self.window)
                 print(f"Error converting tree amount string to float: {expected_amount_str}")
                 return # Stop if we can't even parse the selected row amount
            # -----------------------------------------------------------

            # Now loop through the actual data store
            for i, trans in enumerate(self.transactions):
                # Get values from the stored transaction dictionary
                stored_date = str(trans.get('date', ''))
                stored_account = str(trans.get('account', ''))
                stored_desc = str(trans.get('description', ''))
                stored_type = str(trans.get('type', ''))
                try:
                    # Stored amount should already be a float or convertible
                    stored_amount_float = float(trans.get('amount', -999999.99)) # Use an unlikely default
                except (ValueError, TypeError):
                    print(f"Warning: Non-float amount found in stored transaction: {trans}")
                    continue # Skip comparing this transaction if its amount is corrupt

                # --- Perform the comparison ---
                if (stored_date == expected_date and
                    stored_account == expected_account and
                    stored_desc == expected_desc and
                    stored_type == expected_type and
                    # Compare the floats carefully
                    abs(stored_amount_float - expected_amount_float) < 0.001):
                    transaction_to_delete = trans
                    found_index = i
                    break # Found the match, exit loop

            # --- Process result ---
            if transaction_to_delete is not None and found_index != -1:
                del self.transactions[found_index]
                self.update_transaction_list()
                self.update_balances()
                # self.save_data() # Uncomment for auto-save
                messagebox.showinfo("Success", "Transaction deleted.", parent=self.window)
                desc = transaction_to_delete.get('description', '')
                if TRANSFER_IN_DESC.split('{}')[0] in desc or TRANSFER_OUT_DESC.split('{}')[0] in desc:
                     messagebox.showwarning("Transfer Deleted", "You deleted one part of a transfer. You may need to manually delete the corresponding transaction in the other account for balances to be correct.", parent=self.window)
            else:
                 # This message should now only appear if there's a genuine mismatch
                 messagebox.showerror("Error", "Could not find the selected transaction data to delete. It might have been modified or deleted elsewhere.", parent=self.window)
                 print("Failed to find transaction in list matching:", item_values)
                 # print("Current transactions for debugging:", self.transactions) # Uncomment if needed

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred while deleting: {e}", parent=self.window)
            print(f"Error deleting transaction: {e}")


    # --- Display Updates (Keep as is) ---
    def update_transaction_list(self):
        # ... (no changes needed) ...
        """Clears and repopulates the transaction treeview."""
        for item in self.tree.get_children(): self.tree.delete(item)
        # Sort by date (descending), then potentially by timestamp ID for same-day order
        sorted_transactions = sorted(self.transactions, key=lambda x: (x.get('date', ''), x.get('id', 0)), reverse=True)
        for i, trans in enumerate(sorted_transactions):
            amount = trans.get('amount', 0.0); amount_str = f"{amount:,.2f}" # Add comma formatting
            row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            trans_type = trans.get('type', TRANS_EXPENSE)
            type_tag = 'income' if trans_type == TRANS_INCOME else 'expense'
            tags = (row_tag, type_tag)
            values = (
                trans.get('date', '[No Date]'), trans.get('account', '[No Account]'),
                trans.get('description', '[No Desc]'), trans_type, amount_str
                # Consider adding trans.get('id') here if needed for deletion later
            )
            # Use 'id' field of insert if you want to reference items by transaction ID
            # item_iid = trans.get('id', None) # Get the unique ID
            # self.tree.insert('', tk.END, iid=item_iid, values=values, tags=tags)
            self.tree.insert('', tk.END, values=values, tags=tags) # Simpler insert


    def calculate_balances(self):
        # ... (no changes needed) ...
        """Calculates balances for all accounts and the total."""
        account_balances = defaultdict(float); total_balance = 0.0
        for trans in self.transactions:
            account = trans.get('account'); amount = trans.get('amount', 0.0)
            trans_type = trans.get('type')
            if not account or account not in self.accounts: continue # Ignore trans for deleted accounts
            if trans_type == TRANS_INCOME:
                account_balances[account] += amount; total_balance += amount
            elif trans_type == TRANS_EXPENSE:
                account_balances[account] -= amount; total_balance -= amount
        return account_balances, total_balance

    # update_balances is already cleaned up above

    # --- Data Persistence (Keep as is) ---
    def load_data(self):
        # ... (no changes needed) ...
        """Loads accounts and transactions from the JSON data file."""
        if os.path.exists(FINANCE_DATA_FILE):
            try:
                with open(FINANCE_DATA_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
                if isinstance(data, dict) and "accounts" in data and "transactions" in data:
                    # Load accounts first
                    self.accounts = data.get("accounts", []);
                    if not isinstance(self.accounts, list): self.accounts = []
                    self.accounts.sort() # Sort loaded accounts

                    # Load transactions and validate/clean them
                    loaded_transactions = data.get("transactions", [])
                    if not isinstance(loaded_transactions, list): loaded_transactions = []

                    valid_transactions = []
                    valid_accounts_set = set(self.accounts) # Faster lookup

                    for i, trans in enumerate(loaded_transactions):
                         if isinstance(trans, dict) and all(k in trans for k in ('date', 'account', 'description', 'amount', 'type')):
                             # Check if transaction's account still exists
                             if trans.get('account') not in valid_accounts_set:
                                 print(f"Warn: Skipping trans for non-existent account '{trans.get('account')}': {trans}")
                                 continue # Skip this transaction

                             try: trans['amount'] = float(trans['amount'])
                             except (ValueError, TypeError): trans['amount'] = 0.0 # Default invalid amount to 0

                             if 'id' not in trans or not isinstance(trans['id'], (int, float)):
                                 trans['id'] = datetime.now().timestamp() + i # Assign unique ID if missing/invalid

                             valid_transactions.append(trans)
                         else:
                             print(f"Warn: Skipping invalid trans data format idx {i}: {trans}")
                    self.transactions = valid_transactions
                # ... (rest of old format handling - maybe simplify or remove if not needed)
                elif isinstance(data, list): # Handle old format
                    parent_win = self.window if self.window.winfo_exists() else None
                    messagebox.showwarning("Old Data Format", f"Data file '{FINANCE_DATA_FILE}' is in an old format. Accounts are missing. Adding a 'Default' account for existing transactions.", parent=parent_win)
                    self.transactions = data; self.accounts = []
                    valid_transactions = []; needs_default = False
                    for i, trans in enumerate(self.transactions):
                         if isinstance(trans, dict) and all(k in trans for k in ('date', 'description', 'amount', 'type')):
                             trans['account'] = "Default"; needs_default = True
                             try: trans['amount'] = float(trans['amount'])
                             except (ValueError, TypeError): trans['amount'] = 0.0
                             if 'id' not in trans: trans['id'] = datetime.now().timestamp() + i
                             valid_transactions.append(trans)
                         else: print(f"Warn: Skipping invalid old trans data idx {i}: {trans}")
                    self.transactions = valid_transactions
                    if needs_default and "Default" not in self.accounts: self.accounts = ['Default'] # Add default only if needed
                else:
                    raise ValueError("Unknown data format in file.")

            except json.JSONDecodeError:
                parent_win = self.window if self.window.winfo_exists() else None
                messagebox.showerror("Load Error", f"Could not decode JSON from {FINANCE_DATA_FILE}. Starting fresh.", parent=parent_win)
                self._set_default_state() # Use a helper for default state
            except Exception as e:
                 parent_win = self.window if self.window.winfo_exists() else None
                 messagebox.showerror("Load Error", f"Failed to load data: {e}", parent=parent_win)
                 self._set_default_state() # Use a helper for default state
                 print(f"Error loading data: {e}")
        else:
            print(f"Data file '{FINANCE_DATA_FILE}' not found. Starting with defaults.")
            self._set_default_state() # Use a helper for default state

    def _set_default_state(self):
        """Sets the application to a default empty or sample state."""
        # Option 1: Completely empty
        # self.accounts = []
        # self.transactions = []
        # Option 2: Start with some defaults
        self.accounts = ["Cash", "Debit Card", "E-wallet"];
        self.transactions = []
        self.accounts.sort()


    def save_data(self):
        # ... (no changes needed) ...
        """Saves the current accounts and transactions to the JSON data file."""
        data_to_save = {"accounts": sorted(list(self.accounts)), "transactions": self.transactions} # Ensure accounts are saved sorted
        try:
            with open(FINANCE_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        except IOError as e:
             messagebox.showerror("Save Error", f"Could not save data to {FINANCE_DATA_FILE}:\n{e}", parent=self.window)
             print(f"Error saving data: {e}")
        except Exception as e:
             messagebox.showerror("Save Error", f"An unexpected error occurred during save: {e}", parent=self.window)
             print(f"Unexpected error saving data: {e}")


    def on_closing(self):
        # ... (no changes needed) ...
        """Handles window closing event."""
        # Use parent=self.window for messageboxes within the class
        if messagebox.askokcancel("Quit", "Do you want to save changes and quit?", parent=self.window):
             self.save_data()
             self.window.destroy()

# --- Main Execution (Keep as is) ---
if __name__ == "__main__":
    root = tb.Window(themename=DEFAULT_THEME)
    root.bell = lambda: None # Keep bell disabled
    app = FinanceTrackerApp(root)
    root.mainloop()