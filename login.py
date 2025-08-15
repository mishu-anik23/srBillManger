# login.py
from PyQt6.QtWidgets import QMainWindow, QLabel, QLineEdit, QPushButton, QMessageBox, QVBoxLayout, QWidget
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

class LoginWindow(QMainWindow):
    def __init__(self, open_billing_callback):
        super().__init__()
        self.setWindowTitle("Login")
        self.setFixedSize(400, 300)
        self.open_billing_callback = open_billing_callback
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(QPixmap("assets/logo-sr.jpeg").scaledToWidth(120))
        layout.addWidget(logo)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.check_login)

        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(login_btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def check_login(self):
        if self.username_input.text() == "admin" and self.password_input.text() == "123":
            self.open_billing_callback()
            print("Closing here")
            self.close()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
