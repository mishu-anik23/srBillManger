# main.py
import sys
from PyQt6.QtWidgets import QApplication
from login import LoginWindow
from billing import BillingWindow

class AppManager:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.login = LoginWindow(self.open_billing)
        self.billing = None

    def run(self):
        self.login.show()
        sys.exit(self.app.exec())

    def open_billing(self):
        self.billing = BillingWindow()
        self.billing.show()

if __name__ == "__main__":
    manager = AppManager()
    manager.run()
