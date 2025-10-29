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
        self.subtotal_amount = 0.0
        self.tax_amount = 0.0
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
        
        # Date and Invoice Number
        date_invoice_layout = QHBoxLayout()
        
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
        
        # Invoice Number
        invoice_layout = QHBoxLayout()
        invoice_label = QLabel("Invoice #:")
        invoice_label.setStyleSheet("font-weight: bold;")
        self.invoice_number_input = QLineEdit()
        self.invoice_number_input.setPlaceholderText("e.g., 001, 002, 003")
        self.invoice_number_input.setStyleSheet("padding: 5px; width: 80px;")
        self.invoice_number_input.setText("001")  # Default value
        invoice_layout.addWidget(invoice_label)
        invoice_layout.addWidget(self.invoice_number_input)
        
        date_invoice_layout.addLayout(date_layout)
        date_invoice_layout.addLayout(invoice_layout)
        date_invoice_layout.addStretch()  # Push to the left
        
        logo_section.addLayout(date_invoice_layout)
        main_layout.addLayout(logo_section)

        # Customer Info Section
        cust_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Customer Name")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Phone Number")
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Customer Address")

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
        
        # Tax Selection
        tax_layout = QHBoxLayout()
        tax_label = QLabel("Tax Rate:")
        tax_label.setStyleSheet("font-weight: bold;")
        self.tax_combo = QComboBox()
        self.tax_combo.addItems(["0%", "7%", "19%"])
        self.tax_combo.setCurrentText("7%")  # Default to 7%
        self.tax_combo.currentTextChanged.connect(self.update_tax_calculation)
        self.tax_combo.setStyleSheet("padding: 5px;")
        
        tax_layout.addWidget(tax_label)
        tax_layout.addWidget(self.tax_combo)
        tax_layout.addStretch()
        
        # Total display
        self.subtotal_label = QLabel("Subtotal: €0.00")
        self.subtotal_label.setStyleSheet("font-size: 14px;")
        
        self.tax_label = QLabel("Tax: €0.00")
        self.tax_label.setStyleSheet("font-size: 14px; color: #666;")
        
        self.total_label = QLabel("Total: €0.00")
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        generate_btn = QPushButton("Generate Bill")
        generate_btn.clicked.connect(self.generate_bill)

        download_btn = QPushButton("Download PDF")
        download_btn.clicked.connect(self.download_pdf)

        # Add widgets to layout
        bill_actions.addLayout(tax_layout)
        bill_actions.addWidget(self.subtotal_label)
        bill_actions.addWidget(self.tax_label)
        bill_actions.addWidget(self.total_label)
        bill_actions.addWidget(generate_btn)
        bill_actions.addWidget(download_btn)

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

    def update_tax_calculation(self):
        """Update tax calculation when tax rate changes"""
        self.update_total()

    def get_tax_rate(self):
        """Get the current tax rate as a decimal"""
        tax_text = self.tax_combo.currentText()
        if tax_text == "0%":
            return 0.0
        elif tax_text == "7%":
            return 0.07
        elif tax_text == "19%":
            return 0.19
        return 0.07  # Default to 7%

    def get_invoice_number(self):
        """Generate invoice number in format SR-YYYYMMDD-XXX"""
        date = self.date_picker.date()
        date_str = date.toString("yyyyMMdd")
        invoice_num = self.invoice_number_input.text().zfill(3)  # Pad with zeros
        return f"SR-{date_str}-{invoice_num}"

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
        # Calculate subtotal
        subtotal = 0.0
        for row in range(self.table.rowCount()):
            try:
                subtotal_text = self.table.item(row, 3).text()
                if subtotal_text:
                    subtotal += float(subtotal_text)
            except (ValueError, AttributeError):
                continue
        
        # Calculate tax
        tax_rate = self.get_tax_rate()
        tax_amount = subtotal * tax_rate
        
        # Calculate total
        total = subtotal + tax_amount
        
        # Update labels
        self.subtotal_label.setText(f"Subtotal: €{subtotal:.2f}")
        self.tax_label.setText(f"Tax: €{tax_amount:.2f}")
        self.total_label.setText(f"Total: €{total:.2f}")
        
        # Update instance variables
        self.subtotal_amount = subtotal
        self.tax_amount = tax_amount
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
        # Get selected date and invoice number
        selected_date = self.date_picker.date().toString("dd.MM.yyyy")
        invoice_number = self.get_invoice_number()
        
        html = "<div style='text-align: center; margin-bottom: 20px;'>"
        html += "<h1 style='color: #2E7D32; margin: 0;'>SUNRISE SUPERMARKET</h1>"
        html += "<p style='margin: 5px 0; color: #666;'>Schwarzwald Straße 27, 60528 Frankfurt am Main</p>"
        html += f"<p style='margin: 5px 0;'><b>Invoice:</b> {invoice_number} | <b>Date:</b> {selected_date}</p>"
        html += "</div>"
        
        html += "<hr style='margin: 20px 0;'>"
        html += "<h2>Customer Information</h2>"
        html += f"<p><b>Name:</b> {self.name_input.text()}<br>"
        html += f"<b>Phone:</b> {self.phone_input.text()}<br>"
        html += f"<b>Address:</b> {self.address_input.text()}<br>"
        html += f"<b>Order Type:</b> {self.order_type.currentText()}<br><br>"

        html += "<table border='1' cellpadding='5'><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Subtotal</th></tr>"
        for row in range(self.table.rowCount()):
            html += "<tr>"
            for col in [0, 1, 2, 3]:
                item = self.table.item(row, col)
                html += f"<td>{item.text()}</td>"
            html += "</tr>"
        
        # Add tax breakdown
        tax_rate_text = self.tax_combo.currentText()
        html += f"<tr><td colspan='3'><b>Subtotal</b></td><td><b>€{self.subtotal_amount:.2f}</b></td></tr>"
        html += f"<tr><td colspan='3'><b>Tax ({tax_rate_text})</b></td><td><b>€{self.tax_amount:.2f}</b></td></tr>"
        html += f"<tr style='background-color: #f0f0f0;'><td colspan='3'><b>TOTAL</b></td><td><b>€{self.total_amount:.2f}</b></td></tr>"
        html += "</table>"

        file_path = os.path.abspath("temp_bill.html")
        with open(file_path, "w") as f:
            f.write(html)

        webbrowser.open(f"file://{file_path}")

    def download_pdf(self):
        if not PDF_AVAILABLE:
            QMessageBox.warning(
                self, "PDF Not Available",
                "PDF generation requires the fpdf module.\nPlease install it using: pip install fpdf2"
            )
            return

        invoice_number = self.get_invoice_number()
        selected_date = self.date_picker.date().toString("dd.MM.yyyy")

        pdf = FPDF()
        pdf.add_page()

        # Use a Unicode TrueType font if available (needed for €, ß, ä, etc.)
        font_name = "Arial"
        def _safe_text(txt: str) -> str:
            return txt
        try:
            win_fonts = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
            candidates = [
                os.path.join(win_fonts, "arial.ttf"),
                os.path.join(win_fonts, "segoeui.ttf"),
            ]
            chosen = next((p for p in candidates if os.path.exists(p)), None)
            if chosen:
                pdf.add_font("UI", "", chosen, uni=True)
                pdf.add_font("UI", "B", chosen, uni=True)
                font_name = "UI"
            else:
                def _safe_text(txt: str) -> str:
                    return txt.replace("€", "EUR")
        except Exception:
            def _safe_text(txt: str) -> str:
                return txt.replace("€", "EUR")

        # === SAFE HEADER SECTION ===
        header_y = 12
        header_height = 32

        # Light gray header background (safe bounds)
        pdf.set_fill_color(240, 240, 240)
        pdf.rect(10, header_y, 192, header_height, style="F")

        # --- Logo ---
        try:
            logo_path = "assets/logo-sr.jpeg"
            if os.path.exists(logo_path):
                pdf.image(logo_path, x=12, y=header_y + 2, w=25)
        except:
            pass

        # --- Company Info (to right of logo) ---
        pdf.set_xy(45, header_y + 3)
        pdf.set_font(font_name, "B", 16)
        pdf.cell(100, 8, _safe_text("SUNRISE SUPERMARKET"), ln=0)

        pdf.set_xy(45, header_y + 13)
        pdf.set_font(font_name, size=10)
        pdf.cell(100, 6, _safe_text("Schwarzwald Straße 27"), ln=2)
        pdf.cell(100, 6, _safe_text("60528 Frankfurt am Main"), ln=2)

        # --- Tax and Invoice Info (top-right corner) ---
        pdf.set_xy(140, header_y + 5)
        pdf.set_font(font_name, "B", size=9)
        pdf.cell(60, 5, _safe_text("Tax ID: 01435901405"), ln=2, align="R")
        pdf.cell(60, 5, _safe_text("VAT ID: DE365100311"), ln=2, align="R")
        pdf.cell(60, 5, _safe_text(f"Invoice: {invoice_number}"), ln=2, align="R")
        pdf.cell(60, 5, _safe_text(f"Date: {selected_date}"), ln=2, align="R")

        # --- Separator Line ---
        pdf.set_draw_color(180, 180, 180)
        pdf.set_line_width(0.3)
        pdf.line(10, header_y + header_height + 3, 202, header_y + header_height + 3)

        pdf.ln(18)  # Move cursor down safely

        # === CUSTOMER INFORMATION ===
        pdf.set_font(font_name, "B", 16)
        pdf.cell(200, 8, _safe_text("Customer Information"), ln=True)
        pdf.set_font(font_name, size=10)
        pdf.cell(200, 6, _safe_text(f"Name: {self.name_input.text()}"), ln=True)
        pdf.cell(200, 6, _safe_text(f"Phone: {self.phone_input.text()}"), ln=True)
        pdf.cell(200, 6, _safe_text(f"Address: {self.address_input.text()}"), ln=True)
        pdf.cell(200, 6, _safe_text(f"Order Type: {self.order_type.currentText()}"), ln=True)
        pdf.ln(10)

        # === PRODUCT TABLE HEADER ===
        pdf.set_font(font_name, "B", 10)
        pdf.cell(60, 10, _safe_text("Product"), border=1)
        pdf.cell(30, 10, _safe_text("Qty"), border=1)
        pdf.cell(40, 10, _safe_text("Unit Price"), border=1)
        pdf.cell(40, 10, _safe_text("Subtotal"), border=1)
        pdf.ln()

        # === PRODUCT TABLE DATA ===
        pdf.set_font(font_name, size=10)
        for row in range(self.table.rowCount()):
            for col in [0, 1, 2, 3]:
                item = self.table.item(row, col)
                text = item.text() if item is not None else ""
                pdf.cell([60, 30, 40, 40][col], 10, _safe_text(text), border=1)
            pdf.ln()

        # === TAX BREAKDOWN ===
        tax_rate_text = self.tax_combo.currentText()
        pdf.set_font(font_name, size=10)
        pdf.cell(130, 10, _safe_text("Subtotal"), border=1)
        pdf.cell(40, 10, _safe_text(f"€ {self.subtotal_amount:.2f}"), border=1)
        pdf.ln()

        pdf.cell(130, 10, _safe_text(f"Tax ({tax_rate_text})"), border=1)
        pdf.cell(40, 10, _safe_text(f"€ {self.tax_amount:.2f}"), border=1)
        pdf.ln()

        # === TOTAL ROW ===
        pdf.set_font(font_name, "B", 10)
        pdf.cell(130, 10, _safe_text("TOTAL"), border=1)
        pdf.cell(40, 10, _safe_text(f"€ {self.total_amount:.2f}"), border=1)
        pdf.ln(20)

        # === PAYMENT INFORMATION FOOTER ===
        pdf.set_font(font_name, "B", 10)
        pdf.cell(200, 6, _safe_text("Payment Information"), ln=True, align="L")
        pdf.set_font(font_name, size=9)
        pdf.cell(200, 4, _safe_text("Sunrise International GbR"), ln=True, align="L")
        pdf.cell(200, 4, _safe_text("Zahlungsempfänger: Taher Abu Mohammed"), ln=True, align="L")
        pdf.cell(200, 4, _safe_text("Bankverbindung: Deutsche Bank AG"), ln=True, align="L")
        pdf.cell(200, 4, _safe_text("BIC: DEUTDEFFXXX"), ln=True, align="L")
        pdf.cell(200, 4, _safe_text("IBAN: DE91500700100257091900"), ln=True, align="L")

        # === SAVE FILE ===
        pdf_path = QFileDialog.getSaveFileName(
            self, "Save Bill as PDF", f"invoice_{invoice_number}.pdf", "PDF Files (*.pdf)"
        )[0]
        if pdf_path:
            pdf.output(pdf_path)
            QMessageBox.information(self, "PDF Saved", f"Invoice saved at:\n{pdf_path}")


