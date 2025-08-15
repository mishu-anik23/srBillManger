# billing.py
import sqlite3
import os
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import webbrowser
from fpdf import FPDF
from datetime import datetime


class BillingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Supermarket Billing System")
        self.setFixedSize(1000, 700)

        self.conn = sqlite3.connect("supermarket.db")
        self.cursor = self.conn.cursor()

        self.init_ui()
        self.product_row = 0
        self.total_amount = 0.0

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Logo
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(QPixmap("assets/logo-sr.jpeg").scaledToWidth(120))
        main_layout.addWidget(logo)
        print("Logo Created")

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

    def handle_barcode(self):
        barcode = self.barcode_input.text()
        if not barcode:
            return
        self.cursor.execute("SELECT name, unit_price, category FROM products WHERE barcode = ?", (barcode,))
        result = self.cursor.fetchone()
        if result:
            name, price, category = result
            self.insert_product_row(name, 1, price, barcode, category)
            self.barcode_input.clear()
        else:
            QMessageBox.warning(self, "Product Not Found", f"No product with barcode: {barcode}")

    def insert_product_row(self, name, qty, price, barcode, category):
        row_pos = self.table.rowCount()
        self.table.insertRow(row_pos)

        self.table.setItem(row_pos, 0, QTableWidgetItem(name))
        qty_item = QTableWidgetItem(str(qty))
        price_item = QTableWidgetItem(str(price))
        subtotal = float(price) * qty
        subtotal_item = QTableWidgetItem(f"{subtotal:.2f}")

        self.table.setItem(row_pos, 1, qty_item)
        self.table.setItem(row_pos, 2, price_item)
        self.table.setItem(row_pos, 3, subtotal_item)
        self.table.setItem(row_pos, 4, QTableWidgetItem(barcode))
        self.table.setItem(row_pos, 5, QTableWidgetItem(category))

        qty_item.setFlags(Qt.ItemFlag.ItemIsEditable)
        qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        qty_item.setText(str(qty))
        qty_item.setToolTip("Double-click to edit quantity")

        qty_item.textChanged.connect(lambda: self.update_subtotals())
        self.update_total()

    def update_subtotals(self):
        for row in range(self.table.rowCount()):
            try:
                qty = float(self.table.item(row, 1).text())
                price = float(self.table.item(row, 2).text())
                subtotal = qty * price
                self.table.setItem(row, 3, QTableWidgetItem(f"{subtotal:.2f}"))
            except Exception:
                continue
        self.update_total()

    def update_total(self):
        total = 0.0
        for row in range(self.table.rowCount()):
            try:
                subtotal = float(self.table.item(row, 3).text())
                total += subtotal
            except:
                continue
        self.total_label.setText(f"Total: ${total:.2f}")
        self.total_amount = total

    def add_manual_row(self):
        self.insert_product_row("New Item", 1, 0.00, "-", "vegetable")

    def remove_selected_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.update_total()

    def generate_bill(self):
        html = "<h1>Supermarket Bill</h1>"
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
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Supermarket Bill", ln=True, align="C")
        pdf.cell(200, 10, txt=f"Customer: {self.name_input.text()}", ln=True)
        pdf.cell(200, 10, txt=f"Order Type: {self.order_type.currentText()}", ln=True)
        pdf.ln(10)

        pdf.set_font("Arial", size=10)
        pdf.cell(60, 10, "Product", border=1)
        pdf.cell(30, 10, "Qty", border=1)
        pdf.cell(40, 10, "Unit Price", border=1)
        pdf.cell(40, 10, "Subtotal", border=1)
        pdf.ln()

        for row in range(self.table.rowCount()):
            for col in [0, 1, 2, 3]:
                text = self.table.item(row, col).text()
                pdf.cell([60, 30, 40, 40][col], 10, text, border=1)
            pdf.ln()

        pdf.cell(130, 10, "Total", border=1)
        pdf.cell(40, 10, f"${self.total_amount:.2f}", border=1)
        pdf_path = QFileDialog.getSaveFileName(self, "Save Bill as PDF", "supermarket_bill.pdf", "PDF Files (*.pdf)")[0]
        if pdf_path:
            pdf.output(pdf_path)
            QMessageBox.information(self, "PDF Saved", f"Bill saved at:\n{pdf_path}")
