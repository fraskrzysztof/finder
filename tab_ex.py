import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QLabel
)

class DemoTabs(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Przykład zakładek")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        # === GŁÓWNY WIDGET Z ZAKŁADKAMI ===
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # === TWORZYMY 3 ZAKŁADKI ===
        tab1 = QWidget()
        tab2 = QWidget()
        tab3 = QWidget()

        # === TREŚĆ PIERWSZEJ ZAKŁADKI ===
        tab1_layout = QVBoxLayout()
        tab1_layout.addWidget(QLabel("To jest zakładka 1"))
        tab1.setLayout(tab1_layout)

        # === DRUGA ZAKŁADKA ===
        tab2_layout = QVBoxLayout()
        tab2_layout.addWidget(QLabel("To jest zakładka 2"))
        tab2.setLayout(tab2_layout)

        # === TRZECIA ZAKŁADKA ===
        tab3_layout = QVBoxLayout()
        tab3_layout.addWidget(QLabel("To jest zakładka 3"))
        tab3.setLayout(tab3_layout)

        # === DODAWANIE ZAKŁADEK DO WIDGETU ===
        self.tabs.addTab(tab1, "Ustawienia")
        self.tabs.addTab(tab2, "Kamera")
        self.tabs.addTab(tab3, "Wykresy")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoTabs()
    window.show()
    sys.exit(app.exec())
