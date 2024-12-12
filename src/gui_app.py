import sys
import traceback
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QTextEdit, QLineEdit, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QUrl
from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QDesktopServices
from PyQt5.QtCore import QUrl

from chatbot.atlassian_chatbot import AtlassianChatbot

class ClickableTextEdit(QTextEdit):
    """Benutzerdefiniertes TextEdit mit Hyperlink-Unterstützung"""
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def mousePressEvent(self, event):
        # Prüfe, ob auf einen Link geklickt wurde
        if event.button() == Qt.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            char_format = cursor.charFormat()
            
            # Wenn es ein Hyperlink ist, öffne ihn
            if char_format.isAnchor():
                link_url = char_format.anchorHref()
                QDesktopServices.openUrl(QUrl(link_url))
        
        super().mousePressEvent(event)

class WorkerSignals(QObject):
    """Definiert Signale für den Worker"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(str)

class ChatbotWorker(QThread):
    """Hintergrund-Worker zum Verarbeiten von Chatbot-Antworten"""
    def __init__(self, chatbot, prompt):
        super().__init__()
        self.chatbot = chatbot
        self.prompt = prompt
        self.signals = WorkerSignals()
    
    def run(self):
        try:
            # Verarbeite die Anfrage
            response = self.chatbot.process_conversation(self.prompt)
            # Sende Ergebnis
            self.signals.result.emit(response)
        except Exception as e:
            # Sende Fehler
            error_msg = f"Fehler bei der Verarbeitung: {str(e)}"
            self.signals.error.emit(error_msg)
        finally:
            # Signalisiere Abschluss
            self.signals.finished.emit()

class JiraConfluenceChatApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JIRA & Confluence Chat Assistent")
        self.setGeometry(100, 100, 800, 600)
        
        # Initialisiere Chatbot
        self.chatbot = AtlassianChatbot()
        
        # Verhindere, dass Threads das Programm schließen
        self.active_threads = []
        
        # Haupt-Widget und Layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Chat-Anzeigebereich (nun ClickableTextEdit)
        self.chat_display = ClickableTextEdit()
        self.chat_display.setReadOnly(True)
        
        # Schriftart und -größe verbessert
        font = QFont('Segoe UI', 12)  # Größere, leserlichere Schrift
        self.chat_display.setFont(font)
        
        main_layout.addWidget(self.chat_display)
        
        # Eingabebereich
        input_layout = QHBoxLayout()
        
        # Chat-Eingabefeld
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Stellen Sie Fragen zu JIRA-Tickets oder suchen Sie nach Confluence-Seiten...")
        self.chat_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.chat_input)
        
        # Senden-Button
        self.send_button = QPushButton("Senden")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)
        
        # Eingabelayout zur Hauptlayout hinzufügen
        main_layout.addLayout(input_layout)
        
        # Gedämpftere Farbpalette
        self.setStyleSheet("""
        QWidget {
            background-color: #f0f0f0;
            color: #333333;
        }
        QTextEdit {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
            padding: 10px;
        }
        QLineEdit {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
            padding: 8px;
            font-size: 12px;
        }
        QPushButton {
            background-color: #4a90e2;
            color: #ffffff;
            border: none;
            padding: 8px 15px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #357abd;
        }
        """)
    
    def send_message(self):
        # Eingabe holen
        prompt = self.chat_input.text().strip()
        
        if not prompt:
            return
        
        # Deaktiviere Sendebutton während der Verarbeitung
        self.send_button.setEnabled(False)
        
        # Benutzernachricht anzeigen
        self.display_message("Sie", prompt, is_user=True)
        
        # Eingabefeld leeren
        self.chat_input.clear()
        
        # Neuen Worker erstellen
        worker = ChatbotWorker(self.chatbot, prompt)
        
        # Verbinde Signale
        worker.signals.result.connect(self.display_chatbot_response)
        worker.signals.error.connect(self.handle_worker_error)
        worker.signals.finished.connect(self.on_worker_finished)
        
        # Starte Worker
        worker.start()
        
        # Speichere Thread, um ihn zu verfolgen
        self.active_threads.append(worker)
    
    def display_message(self, sender, message, is_user=False):
        """Nachricht im Chat-Display anzeigen"""
        # Hyperlinks erkennen und formatieren
        def replace_links(text):
            url_pattern = r'(https?://\S+)'
            def replace(match):
                url = match.group(1)
                return f'<a href="{url}">{url}</a>'
            return re.sub(url_pattern, replace, text)
        
        # Nachricht mit Links formatieren
        formatted_message = replace_links(message)
        
        # Farbschema anpassen
        if is_user:
            colored_message = f'<p style="color: #1e88e5;"><strong>{sender}:</strong> {formatted_message}</p>'
        else:
            colored_message = f'<p style="color: #4a4a4a;"><strong>{sender}:</strong> {formatted_message}</p>'
        
        # Nachricht hinzufügen
        self.chat_display.append(colored_message)
    
    def display_chatbot_response(self, response):
        """Chatbot-Antwort anzeigen"""
        self.display_message("Assistent", response)
    
    def handle_worker_error(self, error_msg):
        """Fehler im Worker behandeln"""
        self.display_message("Fehler", error_msg, is_user=False)
    
    def on_worker_finished(self):
        """Aktionen nach Abschluss des Workers"""
        # Entferne den beendeten Thread
        sender = self.sender()
        if sender in self.active_threads:
            self.active_threads.remove(sender)
        
        # Aktiviere Senden-Button wieder
        self.send_button.setEnabled(True)
    
    def closeEvent(self, event):
        """Beim Schließen des Fensters"""
        # Warte auf laufende Threads
        if self.active_threads:
            reply = QMessageBox.question(self, 'Threads aktiv', 
                                         'Es sind noch Threads aktiv. Wirklich beenden?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # Versuche, Threads zu stoppen
                for thread in self.active_threads:
                    thread.quit()
                    thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    app = QApplication(sys.argv)
    chat_app = JiraConfluenceChatApp()
    chat_app.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()