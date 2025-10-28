# billing.py
import sqlite3
import os
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
    QDateEdit
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QDate
import webbrowser
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: fpdf module not available. PDF generation will be disabled.")
from datetime import datetime


class BillingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Supermarket Billing System")
        self.setFixedSize(1000, 700)

        try:
            self.conn = sqlite3.connect("supermarket.db")
            self.cursor = self.conn.cursor()
            print("Database connected successfully")
        except Exception as e:
            print(f"Database connection failed: {e}")
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {e}")
            return

        self.init_ui()
        self.product_row = 0
        self.total_amount = 0.0

    def __del__(self):
        """Clean up database connection when object is destroyed"""
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
                print("Database connection closed")
        except Exception as e:
            print(f"Error closing database: {e}")

    def closeEvent(self, event):
        """Handle window close event"""
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
                print("Database connection closed on window close")
        except Exception as e:
            print(f"Error closing database: {e}")
        event.accept()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Logo and Shop Info Section
        logo_section = QVBoxLayout()
        
        # Logo
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            logo.setPixmap(QPixmap("assets/logo-sr.jpeg").scaledToWidth(150))
            print("Logo Created")
        except Exception as e:
            print(f"Logo loading failed: {e}")
            logo.setText("SUNRISE SUPERMARKET")
            logo.setStyleSheet("font-size: 20px; font-weight: bold; color: #2E7D32;")
        logo_section.addWidget(logo)
        
        # Shop Address
        address_label = QLabel("Schwarzwald Straße 27, 60528 Frankfurt am Main")
        address_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        address_label.setStyleSheet("font-size: 12px; color: #666; margin: 5px;")
        logo_section.addWidget(address_label)
        
        # Date Picker
        date_layout = QHBoxLayout()
        date_label = QLabel("Bill Date:")
        date_label.setStyleSheet("font-weight: bold;")
        self.date_picker = QDateEdit()
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setStyleSheet("padding: 5px;")
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_picker)
        date_layout.addStretch()  # Push to the left
        
        logo_section.addLayout(date_layout)
        main_layout.addLayout(logo_section)

        # Customer Info Section
        cust_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Customer Name")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Phone Number")
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Address")

        self.order_type = QComboBox()
        self.order_type.addItems(["Retail", "Wholesale"])

        for w in [self.name_input, self.phone_input, self.address_input, self.order_type]:
            cust_layout.addWidget(w)

        main_layout.addLayout(cust_layout)

        # Product Entry
        product_entry_layout = QHBoxLayout()
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan or Enter Barcode")
        self.barcode_input.returnPressed.connect(self.handle_barcode)

        add_btn = QPushButton("+")
        add_btn.clicked.connect(self.add_manual_row)
        remove_btn = QPushButton("-")
        remove_btn.clicked.connect(self.remove_selected_row)

        product_entry_layout.addWidget(self.barcode_input)
        product_entry_layout.addWidget(add_btn)
        product_entry_layout.addWidget(remove_btn)
        main_layout.addLayout(product_entry_layout)

        # Product Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Product Name", "Quantity", "Unit Price", "Subtotal", "Barcode", "Category"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Connect table item changed signal for automatic subtotal updates
        self.table.itemChanged.connect(self.on_item_changed)
        
        # Enable editing with double-click and F2 key
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed | QTableWidget.EditTrigger.AnyKeyPressed)
        
        main_layout.addWidget(self.table)

        # Bill Actions
        bill_actions = QHBoxLayout()
        self.total_label = QLabel("Total: $0.00")
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        generate_btn = QPushButton("Generate Bill")
        generate_btn.clicked.connect(self.generate_bill)

        download_btn = QPushButton("Download PDF")
        download_btn.clicked.connect(self.download_pdf)

        for w in [self.total_label, generate_btn, download_btn]:
            bill_actions.addWidget(w)

        main_layout.addLayout(bill_actions)
        self.setLayout(main_layout)

    def on_item_changed(self, item):
        """Handle when a table item is changed"""
        if item is None:
            return
        
        row = item.row()
        col = item.column()
        
        # Only update subtotals if quantity or price changed
        if col in [1, 2]:  # Quantity or Unit Price columns
            self.update_subtotals()

    def handle_barcode(self):
        barcode = self.barcode_input.text()
        if not barcode:
            return
        
        try:
            self.cursor.execute("SELECT name, unit_price, category FROM products WHERE barcode = ?", (barcode,))
            result = self.cursor.fetchone()
            if result:
                name, price, category = result
                self.insert_product_row(name, 1, price, barcode, category)
                self.barcode_input.clear()
            else:
                # Instead of showing a warning, add a manual row for the unknown barcode
                reply = QMessageBox.question(self, "Product Not Found",
                                              f"No product found with barcode: {barcode}\n\nWould you like to add it manually?",
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.insert_product_row("Enter Product Name", 1, 0.00, barcode, "General")
                    # Focus on the product name cell for immediate editing
                    current_row = self.table.rowCount() - 1
                    self.table.setCurrentCell(current_row, 0)
                    self.table.edit(self.table.currentIndex())
                self.barcode_input.clear()
        except Exception as e:
            print(f"Error handling barcode: {e}")
            QMessageBox.warning(self, "Error", f"Error processing barcode: {e}")
            self.barcode_input.clear()

    def insert_product_row(self, name, qty, price, barcode, category):
        row_pos = self.table.rowCount()
        self.table.insertRow(row_pos)

        # Product name - make it editable
        name_item = QTableWidgetItem(name)
        name_item.setFlags(Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.table.setItem(row_pos, 0, name_item)
        
        # Quantity - make it editable
        qty_item = QTableWidgetItem(str(qty))
        qty_item.setFlags(Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        qty_item.setToolTip("Double-click to edit quantity")
        self.table.setItem(row_pos, 1, qty_item)
        
        # Unit price - make it editable
        price_item = QTableWidgetItem(str(price))
        price_item.setFlags(Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        price_item.setToolTip("Double-click to edit price")
        self.table.setItem(row_pos, 2, price_item)

        # Calculate subtotal
        subtotal = float(price) * qty
        subtotal_item = QTableWidgetItem(f"{subtotal:.2f}")
        subtotal_item.setFlags(Qt.ItemFlag.ItemIsSelectable)  # Read-only
        self.table.setItem(row_pos, 3, subtotal_item)

        # Barcode - make it editable
        barcode_item = QTableWidgetItem(barcode)
        barcode_item.setFlags(Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        barcode_item.setToolTip("Double-click to edit barcode")
        self.table.setItem(row_pos, 4, barcode_item)
        
        # Category - make it editable
        category_item = QTableWidgetItem(category)
        category_item.setFlags(Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        category_item.setToolTip("Double-click to edit category")
        self.table.setItem(row_pos, 5, category_item)

        # Connect signals for automatic updates - use itemChanged signal instead
        # We'll connect to the table's itemChanged signal in init_ui

        self.update_total()

    def update_subtotals(self):
        for row in range(self.table.rowCount()):
            try:
                qty_text = self.table.item(row, 1).text()
                price_text = self.table.item(row, 2).text()

                # Validate inputs
                if not qty_text or not price_text:
                    continue

                qty = float(qty_text)
                price = float(price_text)
                subtotal = qty * price
                self.table.setItem(row, 3, QTableWidgetItem(f"{subtotal:.2f}"))
            except (ValueError, AttributeError):
                # If conversion fails, set subtotal to 0
                self.table.setItem(row, 3, QTableWidgetItem("0.00"))
        self.update_total()

    def update_total(self):
        total = 0.0
        for row in range(self.table.rowCount()):
            try:
                subtotal_text = self.table.item(row, 3).text()
                if subtotal_text:
                    subtotal = float(subtotal_text)
                    total += subtotal
            except (ValueError, AttributeError):
                continue
        self.total_label.setText(f"Total: ${total:.2f}")
        self.total_amount = total

    def add_manual_row(self):
        # Add a new row with default values that can be edited
        self.insert_product_row("Enter Product Name", 1, 0.00, "Manual Entry", "General")
        
        # Focus on the product name cell for immediate editing
        current_row = self.table.rowCount() - 1
        if current_row >= 0:
            self.table.setCurrentCell(current_row, 0)
            # Start editing immediately
            self.table.edit(self.table.currentIndex())

    def remove_selected_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.update_total()
        else:
            QMessageBox.information(self, "No Selection", "Please select a row to remove.")

    def generate_bill(self):
        # Get selected date
        selected_date = self.date_picker.date().toString("dd.MM.yyyy")
        
        html = "<div style='text-align: center; margin-bottom: 20px;'>"
        html += "<h1 style='color: #2E7D32; margin: 0;'>SUNRISE SUPERMARKET</h1>"
        html += "<p style='margin: 5px 0; color: #666;'>Schwarzwald Straße 27, 60528 Frankfurt am Main</p>"
        html += f"<p style='margin: 5px 0;'><b>Bill Date:</b> {selected_date}</p>"
        html += "</div>"
        
        html += "<hr style='margin: 20px 0;'>"
        html += "<h2>Customer Information</h2>"
        html += f"<p><b>Name:</b> {self.name_input.text()}<br>"
        html += f"<b>Phone:</b> {self.phone_input.text()}<br>"
        html += f"<b>Order Type:</b> {self.order_type.currentText()}<br><br>"

        html += "<table border='1' cellpadding='5'><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Subtotal</th></tr>"
        for row in range(self.table.rowCount()):
            html += "<tr>"
            for col in [0, 1, 2, 3]:
                item = self.table.item(row, col)
                html += f"<td>{item.text()}</td>"
            html += "</tr>"
        html += f"<tr><td colspan='3'><b>Total</b></td><td><b>${self.total_amount:.2f}</b></td></tr>"
        html += "</table>"

        file_path = os.path.abspath("temp_bill.html")
        with open(file_path, "w") as f:
            f.write(html)

        webbrowser.open(f"file://{file_path}")

    def download_pdf(self):
        if not PDF_AVAILABLE:
            QMessageBox.warning(self, "PDF Not Available", 
                               "PDF generation requires the fpdf module.\nPlease install it using: pip install fpdf2")
            return
        
        # Get selected date
        selected_date = self.date_picker.date().toString("dd.MM.yyyy")
            
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, txt="SUNRISE SUPERMARKET", ln=True, align="C")
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 6, txt="Schwarzwald Straße 27, 60528 Frankfurt am Main", ln=True, align="C")
        pdf.cell(200, 6, txt=f"Bill Date: {selected_date}", ln=True, align="C")
        pdf.ln(10)
        
        # Customer Information
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 8, txt="Customer Information", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 6, txt=f"Name: {self.name_input.text()}", ln=True)
        pdf.cell(200, 6, txt=f"Phone: {self.phone_input.text()}", ln=True)
        pdf.cell(200, 6, txt=f"Order Type: {self.order_type.currentText()}", ln=True)
        pdf.ln(10)

        # Product Table Header
        pdf.set_font("Arial", "B", 10)
        pdf.cell(60, 10, "Product", border=1)
        pdf.cell(30, 10, "Qty", border=1)
        pdf.cell(40, 10, "Unit Price", border=1)
        pdf.cell(40, 10, "Subtotal", border=1)
        pdf.ln()
        
        # Product Table Data
        pdf.set_font("Arial", size=10)

        for row in range(self.table.rowCount()):
            for col in [0, 1, 2, 3]:
                text = self.table.item(row, col).text()
                pdf.cell([60, 30, 40, 40][col], 10, text, border=1)
            pdf.ln()

        # Total row
        pdf.set_font("Arial", "B", 10)
        pdf.cell(130, 10, "TOTAL", border=1)
        pdf.cell(40, 10, f"${self.total_amount:.2f}", border=1)
        pdf_path = QFileDialog.getSaveFileName(self, "Save Bill as PDF", "supermarket_bill.pdf", "PDF Files (*.pdf)")[0]
        if pdf_path:
            pdf.output(pdf_path)
            QMessageBox.information(self, "PDF Saved", f"Bill saved at:\n{pdf_path}")
