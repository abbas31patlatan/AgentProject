# File: gui/qt_app.py

import sys
import asyncio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox, QListWidget
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from core.plugin_loader import PluginLoader

class WorkerThread(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, mind, prompt: str):
        super().__init__()
        self.mind = mind
        self.prompt = prompt

    def run(self):
        # Her thread kendi asyncio loop'una sahip olmalı
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.mind.request(self.prompt))
            self.response_ready.emit(result if isinstance(result, str) else str(result))
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            loop.close()

class QtAgentApp:
    """
    PyQt6 tabanlı ana AgentProject GUI:
    - Sohbet/chat penceresi
    - Persona seçimi
    - Plugin durumu ve hızlı erişim
    - Chat ve komut gönderebilme
    """
    def __init__(self, consciousness, plugin_loader: PluginLoader = None):
        self.consciousness = consciousness
        self.plugin_loader = plugin_loader

        # PyQt app setup
        self.app = QApplication(sys.argv)
        self.window = QMainWindow()
        self.window.setWindowTitle("AgentProject – Tanrısal AI Asistan")

        central = QWidget()
        self.window.setCentralWidget(central)
        layout = QVBoxLayout()
        central.setLayout(layout)

        # Persona seçimi
        persona_layout = QHBoxLayout()
        self.persona_box = QComboBox()
        self.persona_box.addItems(["Standart", "Overlord/Albedo", "Dost", "Kodcu", "Oyun Partneri"])
        persona_label = QLabel("Persona:")
        persona_layout.addWidget(persona_label)
        persona_layout.addWidget(self.persona_box)
        layout.addLayout(persona_layout)

        # Plugin listesi
        self.plugin_list = QListWidget()
        if self.plugin_loader:
            self.plugin_list.addItems(list(self.plugin_loader.list_loaded().keys()))
        layout.addWidget(QLabel("Yüklü Eklentiler:"))
        layout.addWidget(self.plugin_list)

        # Chat display
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        layout.addWidget(self.chat_view)

        # Input field + send button
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Mesajınızı yazın…")
        self.send_button = QPushButton("Gönder")
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)

        # Signals
        self.send_button.clicked.connect(self.on_send)
        self.input_field.returnPressed.connect(self.on_send)
        self.persona_box.currentTextChanged.connect(self.on_persona_changed)

    def on_persona_changed(self, persona):
        self.chat_view.append(f"<i><b>Persona:</b> {persona}</i> olarak değiştirildi.")

    def on_send(self):
        prompt = self.input_field.text().strip()
        if not prompt:
            return
        # Kullanıcı mesajı
        self.chat_view.append(f"<b>Sen:</b> {prompt}")
        self.input_field.clear()
        self.send_button.setEnabled(False)

        # Arkaplan thread ile AI cevabı
        worker = WorkerThread(self.consciousness, prompt)
        worker.response_ready.connect(self.on_response)
        worker.error_occurred.connect(self.on_error)
        worker.finished.connect(lambda: self.send_button.setEnabled(True))
        worker.start()

    def on_response(self, response: str):
        self.chat_view.append(f"<b>AI:</b> {response}")

    def on_error(self, error: str):
        self.chat_view.append(f"<span style='color:red'><b>Hata:</b> {error}</span>")

    def run(self):
        self.window.resize(950, 700)
        self.window.show()
        sys.exit(self.app.exec())
