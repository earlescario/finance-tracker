import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Listbox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from ttkbootstrap.widgets import DateEntry
import json
from datetime import datetime, date # Keep datetime
import os
from collections import defaultdict

# --- Configuration ---
FINANCE_DATA_FILE = "finance_data.json"
DEFAULT_THEME = "darkly"
CURRENCY_SYMBOL = "₱"
TRANS_EXPENSE = "Expense"
TRANS_INCOME = "Income"
TRANSFER_OUT_DESC = "Transfer to {}"
TRANSFER_IN_DESC = "Transfer from {}"
UNCATEGORIZED = "Uncategorized" # Default category

# --- Edit Transaction Dialog ---
class EditTransactionDialog(simpledialog.Dialog):
    """Dialog window for editing an existing transaction."""
    def __init__(self, parent, title, transaction_data, accounts, categories):
        self.transaction_data = transaction_data # Store the original data
        self.accounts = accounts
        self.categories = [UNCATEGORIZED] + sorted(list(categories)) # Add Uncategorized option
        # Data variables for the dialog's fields
        self.date_var = tk.StringVar(value=transaction_data.get('date', ''))
        self.account_var = tk.StringVar(value=transaction_data.get('account', ''))
        self.description_var = tk.StringVar(value=transaction_data.get('description', ''))
        self.amount_var = tk.DoubleVar(value=transaction_data.get('amount', 0.0))
        self.type_var = tk.StringVar(value=transaction_data.get('type', TRANS_EXPENSE))
        # Set category, defaulting if not present or invalid
        current_category = transaction_data.get('category', UNCATEGORIZED)
        if current_category not in self.categories and current_category is not None:
             # Add temporarily if category was deleted but still exists on this transaction
             self.categories.append(current_category)
             self.categories.sort() # Keep sorted
        self.category_var = tk.StringVar(value=current_category or UNCATEGORIZED)

        # Transfer check - disable editing if it's part of a transfer
        self.is_transfer = (TRANSFER_IN_DESC.split('{}')[0] in self.description_var.get() or
                            TRANSFER_OUT_DESC.split('{}')[0] in self.description_var.get())

        super().__init__(parent, title)

    def body(self, master):
        """Creates the dialog body (widgets)."""
        frame = tb.Frame(master, padding=10)
        frame.pack(fill=BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        if self.is_transfer:
            tb.Label(frame, text="Cannot edit transfers directly.\nPlease delete both parts and re-add if needed.",
                     bootstyle=WARNING, wraplength=300).grid(row=0, column=0, columnspan=2, pady=10)
            return frame # Stop building the form if it's a transfer

        # Date
        tb.Label(frame, text="Date:").grid(row=1, column=0, padx=5, pady=3, sticky=W)
        date_entry = DateEntry(frame, bootstyle=PRIMARY, dateformat='%Y-%m-%d', firstweekday=0)
        date_entry.entry.config(textvariable=self.date_var)
        date_entry.grid(row=1, column=1, padx=5, pady=3, sticky=EW)

        # Account
        tb.Label(frame, text="Account:").grid(row=2, column=0, padx=5, pady=3, sticky=W)
        account_combo = tb.Combobox(frame, textvariable=self.account_var, values=self.accounts, state="readonly", bootstyle=PRIMARY)
        account_combo.grid(row=2, column=1, padx=5, pady=3, sticky=EW)

        # Description
        tb.Label(frame, text="Description:").grid(row=3, column=0, padx=5, pady=3, sticky=W)
        desc_entry = tb.Entry(frame, textvariable=self.description_var, bootstyle=PRIMARY)
        desc_entry.grid(row=3, column=1, padx=5, pady=3, sticky=EW)

        # Amount
        tb.Label(frame, text="Amount:").grid(row=4, column=0, padx=5, pady=3, sticky=W)
        amount_entry = tb.Entry(frame, textvariable=self.amount_var, bootstyle=PRIMARY)
        amount_entry.grid(row=4, column=1, padx=5, pady=3, sticky=EW)

        # Type
        tb.Label(frame, text="Type:").grid(row=5, column=0, padx=5, pady=3, sticky=W)
        type_combobox = tb.Combobox(frame, textvariable=self.type_var, values=[TRANS_EXPENSE, TRANS_INCOME], state="readonly", bootstyle=PRIMARY)
        type_combobox.grid(row=5, column=1, padx=5, pady=3, sticky=EW)
        type_combobox.bind('<<ComboboxSelected>>', self.on_type_change) # Update category visibility

        # Category
        self.category_label = tb.Label(frame, text="Category:") # Store refs to show/hide
        self.category_combo = tb.Combobox(frame, textvariable=self.category_var, values=self.categories, state="readonly", bootstyle=PRIMARY)

        self.category_label.grid(row=6, column=0, padx=5, pady=3, sticky=W)
        self.category_combo.grid(row=6, column=1, padx=5, pady=3, sticky=EW)
        self.on_type_change() # Set initial visibility

        return desc_entry # Set initial focus

    def on_type_change(self, event=None):
        """Show category only for Expenses."""
        if self.type_var.get() == TRANS_EXPENSE:
            self.category_label.grid()
            self.category_combo.grid()
        else:
            self.category_label.grid_remove()
            self.category_combo.grid_remove()
            self.category_var.set(UNCATEGORIZED) # Reset category if type changes to Income

    def buttonbox(self):
        """Creates Save and Cancel buttons."""
        if self.is_transfer:
             # Only show Cancel if it's a transfer
            box = tb.Frame(self)
            cancel_btn = tb.Button(box, text="Close", width=10, command=self.cancel, bootstyle=SECONDARY)
            cancel_btn.pack(side=tk.RIGHT, padx=5, pady=5)
            box.pack()
        else:
            # Default OK/Cancel if not a transfer
            super().buttonbox()
            # Rename "OK" to "Save"
            self.ok_button = self.children['!frame'].children['!button'] # Fragile but common way
            self.ok_button.config(text="Save Changes", bootstyle=SUCCESS)

    def validate(self):
        """Validates the input before closing the dialog."""
        if self.is_transfer: # Skip validation if it's a transfer (form is disabled)
            return True

        try:
            date_str = self.date_var.get()
            account = self.account_var.get()
            # description = self.description_var.get().strip() # Optional
            amount = self.amount_var.get()
            trans_type = self.type_var.get()
            category = self.category_var.get() if trans_type == TRANS_EXPENSE else UNCATEGORIZED

            if not date_str: raise ValueError("Date is required.")
            try: datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError: raise ValueError(f"Invalid date format: '{date_str}'. Use YYYY-MM-DD.")
            if not account: raise ValueError("Account is required.")
            if amount <= 0: raise ValueError("Amount must be a positive number.")
            if not trans_type: raise ValueError("Type is required.")
            if trans_type == TRANS_EXPENSE and not category:
                 # If expense, ensure category is set (should default, but check)
                 self.category_var.set(UNCATEGORIZED)
                 category = UNCATEGORIZED
                 # Optionally: raise ValueError("Category is required for expenses.")

            # Note: We don't re-check for sufficient funds on *edit* here,
            # as it might be correcting a past mistake or involve complex reversals.
            # User is responsible for the implications of editing past transactions.

            return True # Validation passed
        except ValueError as e:
            messagebox.showerror("Input Error", str(e), parent=self)
            return False
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during validation: {e}", parent=self)
            return False

    def apply(self):
        """Processes the validated data and returns it."""
        if self.is_transfer:
            self.result = None # Indicate no changes made for transfers
            return

        updated_data = {
            "date": self.date_var.get(),
            "account": self.account_var.get(),
            "description": self.description_var.get().strip(),
            "amount": self.amount_var.get(),
            "type": self.type_var.get(),
            "category": self.category_var.get() if self.type_var.get() == TRANS_EXPENSE else None, # Store None if not expense
            "id": self.transaction_data.get('id') # Keep the original ID
        }
        self.result = updated_data # Store the result

# --- Category Manager Dialog ---
class CategoryManagerDialog(simpledialog.Dialog):
    """Dialog to add/delete expense categories."""
    def __init__(self, parent, title, categories):
        self.categories = sorted(list(categories)) # Work with a sorted copy
        self.new_category_var = tk.StringVar()
        super().__init__(parent, title)

    def body(self, master):
        frame = tb.Frame(master, padding=10)
        frame.pack(fill=BOTH, expand=True)

        list_frame = tb.Frame(frame)
        list_frame.pack(pady=5, fill=BOTH, expand=True)

        self.listbox = Listbox(list_frame, selectmode=tk.SINGLE, height=8, relief="flat")
        self.listbox.pack(side=LEFT, fill=BOTH, expand=True, padx=(0,5))
        for cat in self.categories:
            self.listbox.insert(tk.END, cat)

        scrollbar = tb.Scrollbar(list_frame, orient=VERTICAL, command=self.listbox.yview, bootstyle="round-info")
        scrollbar.pack(side=RIGHT, fill=Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        action_frame = tb.Frame(frame)
        action_frame.pack(pady=5, fill=X)
        action_frame.columnconfigure(0, weight=1)

        self.new_cat_entry = tb.Entry(action_frame, textvariable=self.new_category_var)
        self.new_cat_entry.grid(row=0, column=0, padx=(0,5), pady=2, sticky=EW)
        ToolTip(self.new_cat_entry, text="Enter new category name", bootstyle=(INFO, INVERSE))

        add_btn = tb.Button(action_frame, text="Add", command=self.add_category, bootstyle=SUCCESS)
        add_btn.grid(row=0, column=1, padx=(0,5), pady=2)

        del_btn = tb.Button(action_frame, text="Delete Selected", command=self.delete_category, bootstyle=DANGER)
        del_btn.grid(row=1, column=1, padx=(0,5), pady=2)

        return self.new_cat_entry

    def add_category(self):
        new_cat = self.new_category_var.get().strip()
        if not new_cat:
            messagebox.showwarning("Input Error", "Category name cannot be empty.", parent=self)
            return
        if new_cat in self.categories:
            messagebox.showwarning("Duplicate", f"Category '{new_cat}' already exists.", parent=self)
            return
        if new_cat == UNCATEGORIZED:
             messagebox.showwarning("Reserved", f"'{UNCATEGORIZED}' is a reserved name.", parent=self)
             return

        self.categories.append(new_cat)
        self.categories.sort()
        # Update listbox
        self.listbox.insert(tk.END, new_cat)
        self._sort_listbox()
        self.new_category_var.set("")

    def delete_category(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select a category to delete.", parent=self)
            return

        selected_cat = self.listbox.get(selected_indices[0])
        if selected_cat == UNCATEGORIZED:
            messagebox.showwarning("Cannot Delete", f"Cannot delete the '{UNCATEGORIZED}' category.", parent=self)
            return

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the category '{selected_cat}'?\n(Existing transactions using it will remain, but you won't be able to select it for new ones)", parent=self):
            self.categories.remove(selected_cat)
            self.listbox.delete(selected_indices[0])

    def _sort_listbox(self):
        items = list(self.listbox.get(0, tk.END))
        items.sort()
        self.listbox.delete(0, tk.END)
        for item in items:
            self.listbox.insert(tk.END, item)

    def buttonbox(self):
        box = tb.Frame(self)
        # Rename OK to Close
        w = tb.Button(box, text="Save & Close", width=15, command=self.ok, default=tk.ACTIVE, bootstyle=PRIMARY)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tb.Button(box, text="Cancel", width=10, command=self.cancel, bootstyle=SECONDARY)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def apply(self):
        # Return the final, sorted list of categories
        self.result = sorted(self.categories)


# --- Main Application Class ---
class FinanceTrackerApp:
    def __init__(self, window):
        self.window = window
        self.window.title("Multi-Account Finance Tracker")

        self.style = tb.Style(theme=DEFAULT_THEME)
        self.window.configure(background=self.style.colors.bg)

        self.accounts = []
        self.categories = set([UNCATEGORIZED]) # Use a set for efficient add/check, convert to list for UI
        self.transactions = []
        self.load_data() # Load accounts, categories, transactions

        # --- Tkinter Variables ---
        # Transaction Entry
        self.date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.description_var = tk.StringVar()
        self.amount_var = tk.DoubleVar(value=0.0)
        self.type_var = tk.StringVar(value=TRANS_EXPENSE)
        self.transaction_account_var = tk.StringVar()
        self.transaction_category_var = tk.StringVar(value=UNCATEGORIZED) # Add category var
        # Account Management
        self.new_account_name_var = tk.StringVar()
        self.delete_account_var = tk.StringVar()
        # Transfers
        self.transfer_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.transfer_amount_var = tk.DoubleVar(value=0.0)
        self.transfer_from_account_var = tk.StringVar()
        self.transfer_to_account_var = tk.StringVar()
        # Balances
        self.total_balance_var = tk.StringVar(value=f"Total Balance: {CURRENCY_SYMBOL}0.00")
        self.account_balance_labels = {}
        # Filtering / Reporting
        self.filter_start_date_var = tk.StringVar(value="") # Init empty
        self.filter_end_date_var = tk.StringVar(value="")   # Init empty
        self.filter_account_var = tk.StringVar(value="All Accounts")
        self.filter_category_var = tk.StringVar(value="All Categories")
        self.filter_type_var = tk.StringVar(value="All Types")

        # Set default filter dates (e.g., start of current month)
        today = date.today()
        start_of_month = today.replace(day=1).strftime('%Y-%m-%d')
        self.filter_start_date_var.set(start_of_month)
        self.filter_end_date_var.set(today.strftime('%Y-%m-%d'))

        # --- Build UI and Set Initial State ---
        self.create_widgets()
        self.update_account_comboboxes()
        self.update_category_comboboxes() # New: Update category lists
        self.update_transaction_list()    # Populate treeview (initial full view)
        self.update_balances()
        self.update_report_summary()      # New: Update report area
        self.apply_filters()              # Apply default filters on startup

        # --- Window Closing Behavior ---
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _on_mousewheel(self, event):
        """Scrolls the left canvas vertically with the mouse wheel."""
        # Determine scroll amount based on platform and event delta
        if event.num == 5 or event.delta == -120:  # Scroll down (Windows/Mac) / Linux
            delta = 1
        elif event.num == 4 or event.delta == 120: # Scroll up (Windows/Mac) / Linux
            delta = -1
        else:
            delta = 0 # Should not happen with standard wheels

        if hasattr(self, 'left_canvas'): # Check if canvas exists
             self.left_canvas.yview_scroll(delta, "units")

    def _bind_mousewheel(self, widget):
        """Binds mouse wheel scrolling recursively to a widget and its children."""
        # Bind to the widget itself
        widget.bind("<MouseWheel>", self._on_mousewheel) # Windows/Mac
        widget.bind("<Button-4>", self._on_mousewheel)   # Linux scroll up
        widget.bind("<Button-5>", self._on_mousewheel)   # Linux scroll down

        # Recursively bind to children
        for child in widget.winfo_children():
            self._bind_mousewheel(child) # Recurse!

    def _on_left_frame_configure(self, event=None):
        """Updates the scrollregion of the left canvas."""
        if hasattr(self, 'left_canvas') and hasattr(self, 'left_inner_frame'):
            # Update the scroll region to encompass the inner frame
            self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))       

    def create_widgets(self):
        """Creates the main widgets with a scrollable left panel."""
        main_frame = tb.Frame(self.window, padding=15)
        main_frame.pack(fill=BOTH, expand=True)

        # --- Left Panel Setup (with Scrollbar) ---
        # 1. Outer frame to hold the canvas and scrollbar
        left_panel_outer_frame = tb.Frame(main_frame, padding=(0, 0, 10, 0))
        left_panel_outer_frame.pack(side=LEFT, fill=Y, padx=(0, 10)) # Fill vertically only

        # 2. Create the Canvas
        self.left_canvas = tk.Canvas(left_panel_outer_frame, borderwidth=0, background=self.style.colors.bg) # Use tk.Canvas

        # 3. Create the Vertical Scrollbar
        left_scrollbar = tb.Scrollbar(left_panel_outer_frame, orient=VERTICAL, command=self.left_canvas.yview, bootstyle="round-light") # Match theme better if possible

        # 4. Configure the Canvas to use the Scrollbar
        self.left_canvas.configure(yscrollcommand=left_scrollbar.set)

        # 5. Pack the Scrollbar and Canvas
        left_scrollbar.pack(side=RIGHT, fill=Y)
        self.left_canvas.pack(side=LEFT, fill=BOTH, expand=True) # Canvas fills available space

        # 6. Create the *inner* Frame that will contain the actual widgets
        #    This inner frame is placed *onto* the canvas
        self.left_inner_frame = tb.Frame(self.left_canvas, padding=0) # Padding managed by internal frames now

        # 7. Add the inner frame to the canvas using create_window
        self.left_canvas.create_window((0, 0), window=self.left_inner_frame, anchor="nw") # Place at top-left

        # 8. Bind the <Configure> event of the inner frame to update the scroll region
        self.left_inner_frame.bind("<Configure>", self._on_left_frame_configure)

        # --- Bind Mouse Wheel Scrolling (Essential for good UX) ---
        # Bind scrolling to canvas, inner frame, and recursively to all children within inner frame
        self._bind_mousewheel(self.left_canvas)
        self._bind_mousewheel(self.left_inner_frame) # Also bind to inner frame directly


        # --- Widgets previously in left_panel are now placed in self.left_inner_frame ---

        # --- Input Frame ---
        # Change parent to self.left_inner_frame
        input_frame = tb.LabelFrame(self.left_inner_frame, text="Add Transaction", padding=10, bootstyle=SECONDARY)
        input_frame.pack(fill=X, pady=(0, 10), padx=5) # Add slight padx for scrollbar clearance
        input_frame.columnconfigure(1, weight=1)
        # ... (rest of input_frame content remains the same) ...
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
        self.type_combobox.bind("<<ComboboxSelected>>", self.toggle_category_input) # Link type change to category visibility

        self.category_label = tb.Label(input_frame, text="Category:") # Keep ref
        self.category_combo = tb.Combobox(input_frame, textvariable=self.transaction_category_var, state="readonly", bootstyle=PRIMARY) # Keep ref
        self.category_label.grid(row=5, column=0, padx=5, pady=3, sticky=W)
        self.category_combo.grid(row=5, column=1, padx=5, pady=3, sticky=EW)
        ToolTip(self.category_combo, text="Select expense category", bootstyle=(INFO, INVERSE))
        self.toggle_category_input() # Set initial state based on default type

        self.add_button = tb.Button(input_frame, text="Add Transaction", command=self.add_transaction, bootstyle=SUCCESS)
        self.add_button.grid(row=6, column=0, columnspan=2, pady=8, sticky=EW)


        # --- Account & Category Management Frame ---
        # Change parent to self.left_inner_frame
        mgmt_frame = tb.LabelFrame(self.left_inner_frame, text="Manage", padding=10, bootstyle=SECONDARY)
        mgmt_frame.pack(fill=X, pady=(0, 10), padx=5) # Add slight padx
        mgmt_frame.columnconfigure(1, weight=1)
        # ... (rest of mgmt_frame content remains the same) ...
        tb.Label(mgmt_frame, text="New Acct:").grid(row=0, column=0, padx=5, pady=(5,2), sticky=W)
        self.new_account_entry = tb.Entry(mgmt_frame, textvariable=self.new_account_name_var, bootstyle=PRIMARY)
        self.new_account_entry.grid(row=0, column=1, padx=5, pady=(5,2), sticky=EW)
        ToolTip(self.new_account_entry, text="Enter name for a new account", bootstyle=(INFO, INVERSE))
        self.add_account_button = tb.Button(mgmt_frame, text="Add Acct", command=self.add_account, bootstyle=INFO, width=9)
        self.add_account_button.grid(row=0, column=2, padx=5, pady=(5,2))

        tb.Label(mgmt_frame, text="Delete Acct:").grid(row=1, column=0, padx=5, pady=(2,5), sticky=W)
        self.delete_account_combo = tb.Combobox(mgmt_frame, textvariable=self.delete_account_var, state="readonly", bootstyle=PRIMARY)
        self.delete_account_combo.grid(row=1, column=1, padx=5, pady=(2,5), sticky=EW)
        ToolTip(self.delete_account_combo, text="Select account to delete (must have no transactions)", bootstyle=(INFO, INVERSE))
        self.delete_account_button = tb.Button(mgmt_frame, text="Delete Acct", command=self.delete_account, bootstyle=DANGER, width=9)
        self.delete_account_button.grid(row=1, column=2, padx=5, pady=(2,5))

        ttk.Separator(mgmt_frame, orient=HORIZONTAL).grid(row=2, column=0, columnspan=3, sticky='ew', pady=8)

        self.manage_categories_button = tb.Button(mgmt_frame, text="Manage Categories", command=self.open_category_manager, bootstyle=INFO)
        self.manage_categories_button.grid(row=3, column=0, columnspan=3, pady=(5, 0), sticky=EW)


        # --- Transfer Funds Frame ---
        # Change parent to self.left_inner_frame
        transfer_frame = tb.LabelFrame(self.left_inner_frame, text="Transfer Funds", padding=10, bootstyle=SECONDARY)
        transfer_frame.pack(fill=X, pady=(0, 10), padx=5) # Add slight padx
        transfer_frame.columnconfigure(1, weight=1)
        # ... (rest of transfer_frame content remains the same) ...
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


        # --- RIGHT PANEL (Remains the same) ---
        right_panel = tb.Frame(main_frame)
        right_panel.pack(side=LEFT, fill=BOTH, expand=True)

        # --- Filters & Reporting Frame ---
        # ... (Keep this section as it was) ...
        filter_report_frame = tb.Frame(right_panel)
        filter_report_frame.pack(fill=X, pady=(0, 10))
        filter_frame = tb.LabelFrame(filter_report_frame, text="Filters", padding=10, bootstyle=SECONDARY)
        filter_frame.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        filter_frame.columnconfigure((1, 3, 5), weight=1)
        tb.Label(filter_frame, text="Date:").grid(row=0, column=0, padx=5, pady=3, sticky=W)
        self.filter_start_date_entry = DateEntry(filter_frame, bootstyle=INFO, firstweekday=0, dateformat='%Y-%m-%d')
        self.filter_start_date_entry.entry.config(textvariable=self.filter_start_date_var)
        self.filter_start_date_entry.grid(row=0, column=1, padx=2, pady=3, sticky=EW)
        tb.Label(filter_frame, text="to").grid(row=0, column=2, padx=2, pady=3)
        self.filter_end_date_entry = DateEntry(filter_frame, bootstyle=INFO, firstweekday=0, dateformat='%Y-%m-%d')
        self.filter_end_date_entry.entry.config(textvariable=self.filter_end_date_var)
        self.filter_end_date_entry.grid(row=0, column=3, padx=2, pady=3, sticky=EW)
        tb.Label(filter_frame, text="Account:").grid(row=1, column=0, padx=5, pady=3, sticky=W)
        self.filter_account_combo = tb.Combobox(filter_frame, textvariable=self.filter_account_var, state="readonly", bootstyle=INFO)
        self.filter_account_combo.grid(row=1, column=1, padx=2, pady=3, sticky=EW)
        tb.Label(filter_frame, text="Category:").grid(row=1, column=2, padx=5, pady=3, sticky=W)
        self.filter_category_combo = tb.Combobox(filter_frame, textvariable=self.filter_category_var, state="readonly", bootstyle=INFO)
        self.filter_category_combo.grid(row=1, column=3, padx=2, pady=3, sticky=EW)
        tb.Label(filter_frame, text="Type:").grid(row=0, column=4, padx=5, pady=3, sticky=W)
        self.filter_type_combo = tb.Combobox(filter_frame, textvariable=self.filter_type_var, values=["All Types", TRANS_INCOME, TRANS_EXPENSE], state="readonly", bootstyle=INFO)
        self.filter_type_combo.grid(row=0, column=5, padx=(2,10), pady=3, sticky=EW)
        filter_button_frame = tb.Frame(filter_frame)
        filter_button_frame.grid(row=1, column=4, columnspan=2, padx=5, pady=3, sticky=E)
        self.apply_filter_button = tb.Button(filter_button_frame, text="Apply Filters", command=self.apply_filters, bootstyle=PRIMARY)
        self.apply_filter_button.pack(side=LEFT, padx=(0, 5))
        ToolTip(self.apply_filter_button, text="Update transaction list and report based on filters", bootstyle=(INFO, INVERSE))
        self.clear_filter_button = tb.Button(filter_button_frame, text="Clear Filters", command=self.clear_filters, bootstyle=SECONDARY)
        self.clear_filter_button.pack(side=LEFT)
        ToolTip(self.clear_filter_button, text="Reset filters and show all transactions", bootstyle=(INFO, INVERSE))
        report_frame = tb.LabelFrame(filter_report_frame, text="Filtered Summary", padding=5, bootstyle=SECONDARY)
        report_frame.pack(side=LEFT, fill=BOTH, padx=(5,0))
        self.report_text = tk.Text(report_frame, height=4, width=35, wrap="word", relief="flat", font=("Consolas", 9) if os.name == 'nt' else ("monospace", 9))
        self.report_text.pack(fill=BOTH, expand=True)
        self.report_text.configure(state='disabled')

        # --- Transaction List Frame ---
        # ... (Keep this section as it was) ...
        list_frame = tb.LabelFrame(right_panel, text="Filtered Transactions (Double-click to Edit)", padding=10, bootstyle=SECONDARY)
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        columns = ("date", "account", "description", "category", "type", "amount")
        self.tree = tb.Treeview(list_frame, columns=columns, show='headings', bootstyle=PRIMARY)
        self.tree.heading("date", text="Date"); self.tree.heading("account", text="Account")
        self.tree.heading("description", text="Description"); self.tree.heading("category", text="Category")
        self.tree.heading("type", text="Type"); self.tree.heading("amount", text="Amount")
        self.tree.column("date", width=90, anchor=CENTER); self.tree.column("account", width=100, anchor=W)
        self.tree.column("description", width=180, anchor=W); self.tree.column("category", width=100, anchor=W)
        self.tree.column("type", width=70, anchor=CENTER); self.tree.column("amount", width=90, anchor=E)
        tree_scrollbar = tb.Scrollbar(list_frame, orient=VERTICAL, command=self.tree.yview, bootstyle=ROUND)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.pack(side=RIGHT, fill=Y)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.tree.bind("<Double-1>", self.on_transaction_double_click)
        try:
            dark_row_color = self.style.colors.get('dark') or "#303030"; bg_color = self.style.colors.bg or "#343a40"
            if dark_row_color == bg_color: dark_row_color = self.style.colors.inputbg or "#404040"
            self.tree.tag_configure('oddrow', background=dark_row_color); self.tree.tag_configure('evenrow', background=bg_color)
            self.tree.tag_configure('income', foreground=self.style.colors.success); self.tree.tag_configure('expense', foreground=self.style.colors.danger)
            self.tree.tag_configure('transfer', foreground=self.style.colors.warning)
        except Exception as e:
            print(f"Warning: Could not configure treeview colors: {e}"); self.tree.tag_configure('oddrow', background='#333333'); self.tree.tag_configure('evenrow', background='#272727'); self.tree.tag_configure('income', foreground='green'); self.tree.tag_configure('expense', foreground='red'); self.tree.tag_configure('transfer', foreground='orange')

        # --- Balances Frame ---
        # ... (Keep this section as it was) ...
        balances_frame = tb.LabelFrame(right_panel, text="Account Balances (Unaffected by Filters)", padding=10, bootstyle=SECONDARY)
        balances_frame.pack(fill=X, pady=(0, 5))
        self.account_balances_display_frame = tb.Frame(balances_frame)
        self.account_balances_display_frame.pack(fill=X, pady=(0, 5))
        self.total_balance_label = tb.Label(balances_frame, textvariable=self.total_balance_var, font=("Helvetica", 14, "bold"), anchor=E, bootstyle=PRIMARY)
        self.total_balance_label.pack(fill=X, padx=5, pady=(5, 0))

        # --- Bottom Bar ---
        # ... (Keep this section as it was) ...
        bottom_bar = tb.Frame(right_panel)
        bottom_bar.pack(fill=X, pady=(5,0))
        self.delete_transaction_button = tb.Button(bottom_bar, text="Delete Selected Transaction", command=self.delete_selected_transaction, bootstyle=(DANGER, OUTLINE))
        self.delete_transaction_button.pack(side=LEFT, padx=5)
        ToolTip(self.delete_transaction_button, text="Select a transaction in the list above and click here to delete it.", bootstyle=(INFO, INVERSE))

        # --- Final step: Update canvas scroll region after everything is packed ---
        # Call this once after initial packing to set the initial scroll region
        self.window.update_idletasks() # Ensure widgets dimensions are calculated
        self._on_left_frame_configure()


    # --- UI Update Helpers ---

    def toggle_category_input(self, event=None):
        """Shows or hides the category input based on the selected transaction type."""
        if self.type_var.get() == TRANS_EXPENSE:
            self.category_label.grid()
            self.category_combo.grid()
        else:
            self.category_label.grid_remove()
            self.category_combo.grid_remove()
            self.transaction_category_var.set(UNCATEGORIZED) # Reset category if not expense

    def update_account_comboboxes(self):
        """Updates the values in ALL account selection comboboxes."""
        account_list = sorted(list(self.accounts))
        filter_account_list = ["All Accounts"] + account_list

        self.transaction_account_combo['values'] = account_list
        self.transfer_from_combo['values'] = account_list
        self.transfer_to_combo['values'] = account_list
        self.delete_account_combo['values'] = account_list
        self.filter_account_combo['values'] = filter_account_list

        # Function to clear selection if current value is invalid or set default
        def set_combo_value(combo_var, valid_list, default_value=""):
            if combo_var.get() not in valid_list:
                combo_var.set(default_value)

        set_combo_value(self.transaction_account_var, account_list)
        set_combo_value(self.transfer_from_account_var, account_list)
        set_combo_value(self.transfer_to_account_var, account_list)
        set_combo_value(self.delete_account_var, account_list)
        set_combo_value(self.filter_account_var, filter_account_list, "All Accounts")

    def update_category_comboboxes(self):
        """Updates the values in ALL category selection comboboxes."""
        # Ensure UNCATEGORIZED is always first if it exists
        sorted_categories = sorted(list(self.categories - {UNCATEGORIZED}))
        display_categories = [UNCATEGORIZED] + sorted_categories
        filter_categories = ["All Categories"] + display_categories

        self.category_combo['values'] = display_categories
        self.filter_category_combo['values'] = filter_categories

        # Set default if current value is invalid
        if self.transaction_category_var.get() not in display_categories:
            self.transaction_category_var.set(UNCATEGORIZED)
        if self.filter_category_var.get() not in filter_categories:
            self.filter_category_var.set("All Categories")


    # --- Category Management ---
    def open_category_manager(self):
        """Opens the dialog to manage categories."""
        dialog = CategoryManagerDialog(self.window, "Manage Expense Categories", self.categories)
        if dialog.result: # If user clicked Save & Close (result is the list)
             updated_categories = set(dialog.result)
             if updated_categories != self.categories:
                 self.categories = updated_categories
                 self.update_category_comboboxes()
                 self.save_data() # Save changes to categories immediately
                 # Optionally re-apply filters if categories changed significantly
                 # self.apply_filters()
                 # May need to update displayed transactions if a category was deleted?
                 # self.update_transaction_list(self.get_filtered_transactions()) # Refresh view


    # --- Filtering and Reporting ---

    def get_filtered_transactions(self):
        """Applies filters and returns the list of matching transactions."""
        filtered_list = []
        try:
            # Get filter values
            start_date_str = self.filter_start_date_var.get()
            end_date_str = self.filter_end_date_var.get()
            filter_account = self.filter_account_var.get()
            filter_category = self.filter_category_var.get()
            filter_type = self.filter_type_var.get()

            # Validate and parse dates
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

            if start_date and end_date and start_date > end_date:
                 messagebox.showwarning("Filter Error", "Start date cannot be after end date.", parent=self.window)
                 return self.transactions # Return all if dates are invalid

            for trans in self.transactions:
                # Date check
                trans_date = datetime.strptime(trans.get('date', '1900-01-01'), '%Y-%m-%d').date()
                if start_date and trans_date < start_date: continue
                if end_date and trans_date > end_date: continue

                # Account check
                if filter_account != "All Accounts" and trans.get('account') != filter_account:
                    continue

                # Type Check
                if filter_type != "All Types" and trans.get('type') != filter_type:
                    continue

                # Category Check (Only apply if type is Expense or All Types)
                # Important: Check the *transaction's* type, not the filter type here
                trans_type_actual = trans.get('type')
                if trans_type_actual == TRANS_EXPENSE and filter_category != "All Categories":
                     # Handle cases where old transactions might have None category
                     trans_category = trans.get('category') or UNCATEGORIZED
                     if trans_category != filter_category:
                         continue
                elif filter_type == TRANS_EXPENSE and filter_category != "All Categories" and trans_type_actual != TRANS_EXPENSE:
                    # If filtering specifically for Expenses AND a category, skip non-expenses
                    continue

                filtered_list.append(trans)

            return filtered_list

        except ValueError as e:
            messagebox.showerror("Filter Error", f"Invalid date format in filters. Please use YYYY-MM-DD.\n({e})", parent=self.window)
            return self.transactions # Return all on date parse error
        except Exception as e:
            messagebox.showerror("Filter Error", f"An unexpected error occurred while filtering: {e}", parent=self.window)
            print(f"Filter Error: {e}")
            return self.transactions # Return all on other errors

    def apply_filters(self):
        """Gets filtered transactions and updates the list view and report."""
        filtered_data = self.get_filtered_transactions()
        self.update_transaction_list(filtered_data) # Update Treeview
        self.update_report_summary(filtered_data)  # Update Text Summary

    def clear_filters(self):
        """Resets filters to defaults and updates the view."""
        today = date.today()
        start_of_month = today.replace(day=1).strftime('%Y-%m-%d')
        self.filter_start_date_var.set(start_of_month)
        self.filter_end_date_var.set(today.strftime('%Y-%m-%d'))
        self.filter_account_var.set("All Accounts")
        self.filter_category_var.set("All Categories")
        self.filter_type_var.set("All Types")
        self.apply_filters() # Re-apply cleared filters

    def update_report_summary(self, transactions_to_summarize=None):
        """Calculates and displays a summary based on the provided transactions."""
        if transactions_to_summarize is None:
             # If called without specific list, use all transactions (e.g., initial load)
             # Or perhaps better: use currently filtered transactions? Let's use filtered.
             transactions_to_summarize = self.get_filtered_transactions()

        total_income = 0.0
        total_expense = 0.0
        expenses_by_category = defaultdict(float)

        for trans in transactions_to_summarize:
            amount = trans.get('amount', 0.0)
            trans_type = trans.get('type')
            if trans_type == TRANS_INCOME:
                total_income += amount
            elif trans_type == TRANS_EXPENSE:
                total_expense += amount
                category = trans.get('category') or UNCATEGORIZED
                expenses_by_category[category] += amount

        # Prepare report string
        report_str = f"Income:  {CURRENCY_SYMBOL}{total_income:,.2f}\n"
        report_str += f"Expense: {CURRENCY_SYMBOL}{total_expense:,.2f}\n"
        net_change = total_income - total_expense
        sign = "+" if net_change >= 0 else ""
        report_str += f"Net:     {sign}{CURRENCY_SYMBOL}{net_change:,.2f}\n"
        report_str += "-" * 25 + "\n" # Separator

        if expenses_by_category:
            report_str += "Expenses by Category:\n"
            # Sort categories by amount descending for the report
            sorted_categories = sorted(expenses_by_category.items(), key=lambda item: item[1], reverse=True)
            max_cat_len = max(len(cat) for cat in expenses_by_category.keys()) if expenses_by_category else 10
            for category, amount in sorted_categories:
                report_str += f"  {category:<{max_cat_len}} : {CURRENCY_SYMBOL}{amount:>10,.2f}\n" # Align amounts
        else:
             report_str += "(No expenses in filtered period)\n"


        # Update the text widget
        self.report_text.configure(state='normal') # Enable writing
        self.report_text.delete(1.0, tk.END) # Clear previous content
        self.report_text.insert(tk.END, report_str)
        self.report_text.configure(state='disabled') # Disable writing


    # --- Transaction Handling (Add, Edit, Delete) ---

    def add_transaction(self):
        """Adds a new income or expense transaction."""
        try:
            date_str = self.date_var.get()
            account = self.transaction_account_var.get()
            description = self.description_var.get().strip()
            amount = self.amount_var.get()
            trans_type = self.type_var.get()
            # Get category only if it's an expense
            category = self.transaction_category_var.get() if trans_type == TRANS_EXPENSE else None # Store None if not expense

            # --- Validation ---
            if not date_str: raise ValueError("Please select a valid date.")
            try: datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError: raise ValueError(f"Invalid date format: '{date_str}'. Use YYYY-MM-DD.")
            if not account: raise ValueError("Please select an account.")
            if amount <= 0: raise ValueError("Amount must be a positive number.")
            if not trans_type: raise ValueError("Please select a transaction type.")
            if trans_type == TRANS_EXPENSE and not category:
                 # This should be handled by defaulting, but double-check
                 self.transaction_category_var.set(UNCATEGORIZED)
                 category = UNCATEGORIZED
                 # raise ValueError("Please select a category for the expense.") # Or just default


            # --- Insufficient Funds Check ---
            if trans_type == TRANS_EXPENSE:
                account_balances, _ = self.calculate_balances() # Use full calculation
                current_balance = account_balances.get(account, 0.0)
                if current_balance < amount:
                    if not messagebox.askyesno( # Make it a warning confirmation
                        "Insufficient Funds",
                        f"This expense of {CURRENCY_SYMBOL}{amount:,.2f} exceeds the current balance of {CURRENCY_SYMBOL}{current_balance:,.2f} in account '{account}'.\n\nDo you want to add it anyway?",
                        icon='warning', parent=self.window):
                         return # Stop if user clicks No

            # --- Add Transaction ---
            transaction = {
                "date": date_str, "account": account, "description": description,
                "amount": amount, "type": trans_type, "category": category, # Add category
                "id": datetime.now().timestamp() # Unique ID
            }
            self.transactions.append(transaction)
            self.apply_filters() # Update view based on filters
            self.update_balances()
            # self.save_data() # Consider saving more frequently or just on close

            # Reset relevant fields
            self.description_var.set("")
            self.amount_var.set(0.0)
            self.transaction_category_var.set(UNCATEGORIZED) # Reset category dropdown
            self.desc_entry.focus_set()

        except ValueError as e:
            messagebox.showerror("Input Error", str(e), parent=self.window)
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=self.window)
            print(f"Error adding transaction: {e}")

    def on_transaction_double_click(self, event):
        """Handles double-click event on the transaction list."""
        selected_item = self.tree.focus() # Get the item that has focus
        if not selected_item:
            return # Nothing selected
        self.edit_transaction(selected_item)

    def edit_selected_transaction(self):
         """Handles click on an 'Edit' button (if added)."""
         selected_items = self.tree.selection()
         if not selected_items:
            messagebox.showwarning("No Selection", "Please select a transaction to edit.", parent=self.window)
            return
         self.edit_transaction(selected_items[0]) # Edit the first selected

    def edit_transaction(self, item_iid):
        """Opens the edit dialog for the transaction with the given treeview IID."""
        try:
            # Find the original transaction dictionary using the IID (which stores the transaction's unique ID)
            transaction_to_edit = None
            original_index = -1
            for i, trans in enumerate(self.transactions):
                if str(trans.get('id')) == str(item_iid): # Compare IDs as strings just in case
                    transaction_to_edit = trans
                    original_index = i
                    break

            if not transaction_to_edit:
                messagebox.showerror("Error", "Could not find the selected transaction data to edit.", parent=self.window)
                print(f"Edit error: Could not find transaction with ID {item_iid}")
                return

            # Open the dialog
            dialog = EditTransactionDialog(self.window, "Edit Transaction",
                                         transaction_to_edit, self.accounts, self.categories)

            # If the dialog returns valid data (user clicked Save)
            if dialog.result:
                updated_data = dialog.result
                # --- Insufficient Funds Check (on changing to Expense or increasing amount) ---
                is_new_expense = (updated_data['type'] == TRANS_EXPENSE and
                                 transaction_to_edit.get('type') != TRANS_EXPENSE)
                is_increased_expense = (updated_data['type'] == TRANS_EXPENSE and
                                      transaction_to_edit.get('type') == TRANS_EXPENSE and
                                      updated_data['amount'] > transaction_to_edit.get('amount', 0))
                is_new_transfer_out = (updated_data['type'] == TRANS_EXPENSE and
                                       TRANSFER_OUT_DESC.split('{}')[0] in updated_data['description']) # Could refine check

                if is_new_expense or is_increased_expense or is_new_transfer_out:
                    # Calculate potential impact *without* the old transaction but *with* the new
                    temp_transactions = self.transactions[:original_index] + self.transactions[original_index+1:] + [updated_data]
                    account_balances, _ = self.calculate_balances(transactions_list=temp_transactions) # Calc with hypothetical change
                    target_account = updated_data['account']
                    new_balance = account_balances.get(target_account, 0.0)

                    if new_balance < 0:
                         # Use askyesno warning similar to add_transaction
                         if not messagebox.askyesno(
                             "Potential Insufficient Funds",
                             f"Editing this transaction might result in a negative balance ({CURRENCY_SYMBOL}{new_balance:,.2f}) for account '{target_account}'.\n\nDo you want to save the changes anyway?",
                             icon='warning', parent=self.window):
                              return # Stop if user clicks No

                # Replace the old transaction with the updated data in the main list
                self.transactions[original_index] = updated_data
                self.apply_filters()   # Update Treeview and report
                self.update_balances() # Update balance displays
                # self.save_data()       # Optional: save immediately

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while trying to edit: {e}", parent=self.window)
            print(f"Edit Transaction Error: {e}")


    def delete_selected_transaction(self):
        """Deletes the selected transaction(s) from the list."""
        selected_items = self.tree.selection() # Get selected IIDs
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select transaction(s) to delete.", parent=self.window)
            return

        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete the selected {len(selected_items)} transaction(s)?\n(Deleting one part of a transfer will require manually deleting the other)", parent=self.window):
            return

        deleted_count = 0
        found_transfer = False
        ids_to_delete = set(selected_items) # Use a set for faster lookup

        # Iterate backwards through the main list to avoid index issues during deletion
        indices_to_delete = []
        for i in range(len(self.transactions) - 1, -1, -1):
            trans_id = str(self.transactions[i].get('id'))
            if trans_id in ids_to_delete:
                indices_to_delete.append(i)
                desc = self.transactions[i].get('description', '')
                if TRANSFER_IN_DESC.split('{}')[0] in desc or TRANSFER_OUT_DESC.split('{}')[0] in desc:
                     found_transfer = True

        if not indices_to_delete:
             messagebox.showerror("Error", "Could not find the selected transaction data to delete. It might have already been deleted.", parent=self.window)
             print("Delete Error: No matching IDs found in self.transactions for selected IIDs:", selected_items)
             return

        # Perform deletions
        for index in sorted(indices_to_delete, reverse=True): # Delete from end to start
             del self.transactions[index]
             deleted_count += 1

        if deleted_count > 0:
            self.apply_filters()   # Update view
            self.update_balances() # Update balances
            # self.save_data()       # Optional: save immediately
            messagebox.showinfo("Success", f"{deleted_count} transaction(s) deleted.", parent=self.window)
            if found_transfer:
                 messagebox.showwarning("Transfer Deleted", "You deleted one part of a transfer. You may need to manually delete the corresponding transaction in the other account for balances to be correct.", parent=self.window)
        else:
            # This case should be less likely now with the check above
            messagebox.showerror("Error", "Failed to delete the selected transaction(s).", parent=self.window)


    # --- Display Updates ---
    def update_transaction_list(self, transactions_to_display=None):
        """Clears and repopulates the transaction treeview with given data."""
        if transactions_to_display is None:
            transactions_to_display = self.transactions # Default to all if none provided

        for item in self.tree.get_children(): self.tree.delete(item)

        # Sort by date (descending), then by timestamp ID for same-day order
        sorted_transactions = sorted(transactions_to_display, key=lambda x: (x.get('date', '0'), x.get('id', 0)), reverse=True)

        for i, trans in enumerate(sorted_transactions):
            amount = trans.get('amount', 0.0)
            amount_str = f"{amount:,.2f}"
            row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            trans_type = trans.get('type', TRANS_EXPENSE)
            type_tag = 'income' if trans_type == TRANS_INCOME else 'expense'

            # Get category, default if None or missing
            category_str = trans.get('category') or (UNCATEGORIZED if trans_type == TRANS_EXPENSE else "")

            # Check for transfer for optional highlighting
            desc = trans.get('description', '')
            is_transfer = (TRANSFER_IN_DESC.split('{}')[0] in desc or
                           TRANSFER_OUT_DESC.split('{}')[0] in desc)
            tags = (row_tag, type_tag)
            if is_transfer:
                 tags += ('transfer',) # Add transfer tag

            values = (
                trans.get('date', '[No Date]'),
                trans.get('account', '[No Account]'),
                desc,
                category_str, # Added category value
                trans_type,
                amount_str
            )
            # Use the transaction's unique ID as the Treeview item ID (iid)
            # This makes finding the transaction later for editing/deletion reliable
            item_iid = str(trans.get('id'))
            self.tree.insert('', tk.END, iid=item_iid, values=values, tags=tags)

    def update_balances(self):
        """Calculates and updates all balance displays. Uses ALL transactions."""
        # IMPORTANT: Balance calculation should ALWAYS use the full transaction list,
        # regardless of filters applied to the view.
        account_balances, total_balance = self.calculate_balances(transactions_list=self.transactions) # Pass the full list explicitly

        total_balance_color = SUCCESS if total_balance >= 0 else DANGER
        self.total_balance_label.config(bootstyle=total_balance_color)
        self.total_balance_var.set(f"Total Balance: {CURRENCY_SYMBOL}{total_balance:,.2f}")

        for widget in self.account_balances_display_frame.winfo_children(): widget.destroy()
        self.account_balance_labels.clear()
        col_count = 0; max_cols = 3; row_num = 0 # Adjust max_cols as needed
        for account_name in sorted(self.accounts): # Use the globally known accounts
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


    def calculate_balances(self, transactions_list=None):
        """Calculates balances based on a specific list of transactions."""
        if transactions_list is None:
             transactions_list = self.transactions # Default to the main list

        account_balances = defaultdict(float); total_balance = 0.0
        valid_accounts_set = set(self.accounts) # Use the globally known accounts

        for trans in transactions_list:
            account = trans.get('account'); amount = trans.get('amount', 0.0)
            trans_type = trans.get('type')

            # Check if the transaction's account is currently valid
            if not account or account not in valid_accounts_set:
                # Optionally log this, but don't include in balance calculation
                # print(f"Skipping balance calc for transaction with deleted/invalid account '{account}': {trans}")
                continue

            if trans_type == TRANS_INCOME:
                account_balances[account] += amount
                total_balance += amount
            elif trans_type == TRANS_EXPENSE:
                account_balances[account] -= amount
                total_balance -= amount

        # Ensure all known accounts have an entry, even if zero balance
        for acc in self.accounts:
             if acc not in account_balances:
                 account_balances[acc] = 0.0

        return account_balances, total_balance


    # --- Data Persistence ---
    def load_data(self):
        """Loads accounts, categories, and transactions from the JSON data file."""
        if os.path.exists(FINANCE_DATA_FILE):
            try:
                with open(FINANCE_DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, dict) and ("accounts" in data or "transactions" in data): # More flexible check
                    # Load Accounts
                    loaded_accounts = data.get("accounts", [])
                    if not isinstance(loaded_accounts, list): loaded_accounts = []
                    self.accounts = sorted(list(set(loaded_accounts))) # Ensure unique and sorted

                    # Load Categories
                    loaded_categories = data.get("categories", [UNCATEGORIZED]) # Default includes Uncategorized
                    if not isinstance(loaded_categories, list): loaded_categories = [UNCATEGORIZED]
                    self.categories = set(loaded_categories)
                    self.categories.add(UNCATEGORIZED) # Ensure default is always present

                    # Load Transactions
                    loaded_transactions = data.get("transactions", [])
                    if not isinstance(loaded_transactions, list): loaded_transactions = []

                    valid_transactions = []
                    valid_accounts_set = set(self.accounts)

                    for i, trans in enumerate(loaded_transactions):
                         if isinstance(trans, dict) and all(k in trans for k in ('date', 'account', 'description', 'amount', 'type')):
                             # Check if transaction's account still exists (allow loading anyway for history)
                             # if trans.get('account') not in valid_accounts_set:
                             #     print(f"Warn: Loading trans for non-existent account '{trans.get('account')}': {trans}")
                             #     # Keep it for history, but balance calc will ignore it

                             try: trans['amount'] = float(trans['amount'])
                             except (ValueError, TypeError): trans['amount'] = 0.0

                             # Add 'id' if missing (important for editing/deleting)
                             if 'id' not in trans or not isinstance(trans['id'], (int, float, str)): # Allow string IDs too
                                 trans['id'] = datetime.now().timestamp() + i

                             # Add 'category' field if missing (default to Uncategorized for old expense data)
                             if 'category' not in trans:
                                 trans['category'] = UNCATEGORIZED if trans.get('type') == TRANS_EXPENSE else None

                             valid_transactions.append(trans)
                         else:
                             print(f"Warn: Skipping invalid trans data format idx {i}: {trans}")
                    self.transactions = valid_transactions

                elif isinstance(data, list): # Handle very old format (transactions only)
                    print("Warning: Old data format detected (transactions only).")
                    self._set_default_state() # Start with default accounts/categories
                    # Try to load the transactions, assuming default account/category
                    old_transactions = data
                    valid_transactions = []
                    if "Default" not in self.accounts: self.accounts.append("Default")
                    valid_accounts_set = set(self.accounts)

                    for i, trans in enumerate(old_transactions):
                         if isinstance(trans, dict) and all(k in trans for k in ('date', 'description', 'amount', 'type')):
                              try: trans['amount'] = float(trans['amount'])
                              except (ValueError, TypeError): trans['amount'] = 0.0
                              trans['account'] = "Default"
                              trans['category'] = UNCATEGORIZED if trans.get('type') == TRANS_EXPENSE else None
                              trans['id'] = datetime.now().timestamp() + i
                              valid_transactions.append(trans)
                         else:
                              print(f"Warn: Skipping invalid old trans data idx {i}: {trans}")
                    self.transactions = valid_transactions

                else:
                    raise ValueError("Unknown or empty data format in file.")

            except json.JSONDecodeError:
                messagebox.showerror("Load Error", f"Could not decode JSON from {FINANCE_DATA_FILE}. Starting fresh or with backup if available.", parent=self.window if self.window.winfo_exists() else None)
                self._set_default_state()
            except Exception as e:
                 messagebox.showerror("Load Error", f"Failed to load data: {e}", parent=self.window if self.window.winfo_exists() else None)
                 self._set_default_state()
                 print(f"Error loading data: {e}")
        else:
            print(f"Data file '{FINANCE_DATA_FILE}' not found. Starting with defaults.")
            self._set_default_state()

    def _set_default_state(self):
        """Sets the application to a default empty or sample state."""
        self.accounts = ["Cash", "Debit Card", "E-wallet"]
        self.categories = {UNCATEGORIZED, "Groceries", "Salary", "Utilities", "Rent", "Transport"} # Add some defaults
        self.transactions = []
        self.accounts.sort()

    def save_data(self):
        """Saves the current accounts, categories, and transactions to JSON."""
        data_to_save = {
            "accounts": sorted(list(self.accounts)),
            "categories": sorted(list(self.categories)), # Save categories as a sorted list
            "transactions": self.transactions
        }
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
        """Handles window closing event, prompts to save."""
        if messagebox.askokcancel("Quit", "Do you want to save changes and quit?", parent=self.window):
             self.save_data()
             self.window.destroy()

    # --- Account/Transfer Functions (Largely unchanged) ---
    def add_account(self):
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
        self.update_balances() # Balances depend on accounts list
        self.new_account_name_var.set("")
        # self.save_data() # Save immediately or on close
        messagebox.showinfo("Success", f"Account '{new_name}' added.", parent=self.window)

    def delete_account(self):
        """Deletes the selected account if it has no transactions."""
        account_to_delete = self.delete_account_var.get()
        if not account_to_delete:
            messagebox.showwarning("Selection Error", "Please select an account to delete.", parent=self.window)
            return

        # Safety Check: Ensure account has no transactions
        has_transactions = False
        for trans in self.transactions:
            if trans.get('account') == account_to_delete:
                has_transactions = True
                break

        if has_transactions:
            messagebox.showerror("Deletion Prevented", f"Cannot delete account '{account_to_delete}' because it has existing transactions.\nPlease delete or reassign its transactions first (by editing them).", parent=self.window)
            return

        # Confirmation
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete the account '{account_to_delete}'?\nThis account currently has no transactions.", parent=self.window):
            try:
                self.accounts.remove(account_to_delete)
                self.update_account_comboboxes()
                self.update_balances() # Re-calculate balances without the deleted account
                self.apply_filters()   # Re-apply filters as available accounts changed
                self.delete_account_var.set("")
                # self.save_data()
                messagebox.showinfo("Success", f"Account '{account_to_delete}' deleted.", parent=self.window)
            except ValueError:
                messagebox.showerror("Error", f"Account '{account_to_delete}' not found (this shouldn't happen).", parent=self.window)
            except Exception as e:
                 messagebox.showerror("Error", f"An unexpected error occurred while deleting account: {e}", parent=self.window)
                 print(f"Error deleting account: {e}")

    def transfer_funds(self):
        """Creates two transactions to represent a transfer between accounts."""
        try:
            date_str = self.transfer_date_var.get()
            from_account = self.transfer_from_account_var.get()
            to_account = self.transfer_to_account_var.get()
            amount = self.transfer_amount_var.get()

            # Validation
            if not date_str: raise ValueError("Please select a valid date for the transfer.")
            try: datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError: raise ValueError(f"Invalid date format: '{date_str}'. Use YYYY-MM-DD.")
            if not from_account or not to_account: raise ValueError("Please select both 'From' and 'To' accounts.")
            if from_account == to_account: raise ValueError("'From' and 'To' accounts cannot be the same.")
            if amount <= 0: raise ValueError("Transfer amount must be positive.")

            # Insufficient Funds Check for Transfer Out
            account_balances, _ = self.calculate_balances() # Use full calculation
            current_balance_from = account_balances.get(from_account, 0.0)
            if current_balance_from < amount:
                # Use askyesno warning
                 if not messagebox.askyesno(
                     "Insufficient Funds",
                     f"Cannot transfer {CURRENCY_SYMBOL}{amount:,.2f}.\nAccount '{from_account}' only has {CURRENCY_SYMBOL}{current_balance_from:,.2f}.\n\nProceed anyway (account will become negative)?",
                     icon='warning', parent=self.window):
                      return # Stop if user clicks No

            # Create Transfer transactions
            transfer_time = datetime.now().timestamp()
            transfer_id_out = f"tf_out_{transfer_time}"
            transfer_id_in = f"tf_in_{transfer_time}"

            # Transfers don't typically have user-defined categories
            trans_out = {
                "date": date_str, "account": from_account,
                "description": TRANSFER_OUT_DESC.format(to_account),
                "amount": amount, "type": TRANS_EXPENSE, "category": None, "id": transfer_id_out
            }
            trans_in = {
                "date": date_str, "account": to_account,
                "description": TRANSFER_IN_DESC.format(from_account),
                "amount": amount, "type": TRANS_INCOME, "category": None, "id": transfer_id_in
            }
            self.transactions.append(trans_out)
            self.transactions.append(trans_in)
            self.apply_filters()   # Update view
            self.update_balances() # Update balances
            # self.save_data()

            self.transfer_amount_var.set(0.0)
            self.transfer_from_account_var.set("")
            self.transfer_to_account_var.set("")
            messagebox.showinfo("Success", f"Transferred {CURRENCY_SYMBOL}{amount:,.2f} from '{from_account}' to '{to_account}'.", parent=self.window)
        except ValueError as e:
            messagebox.showerror("Input Error", str(e), parent=self.window)
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred during transfer: {e}", parent=self.window)
            print(f"Error transferring funds: {e}")


# --- Main Execution ---
if __name__ == "__main__":
    # root = tk.Tk() # Use tk.Tk if ttkbootstrap Window causes issues with dialogs
    root = tb.Window(themename=DEFAULT_THEME)
    root.bell = lambda: None # Keep bell disabled
    app = FinanceTrackerApp(root)
    root.mainloop()