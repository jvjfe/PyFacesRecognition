from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QFileDialog, QMessageBox, QInputDialog, QTextEdit, QListWidget,
    QListWidgetItem, QLineEdit, QDialog, QDialogButtonBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import os, cv2, json, numpy as np
from datetime import datetime

from .utils import (
    load_known_faces, save_known_faces, get_face_encoding, compare_faces,
    load_cards, save_cards, faces_dir
)
from .dialogs import CaptureDialog, aguardar_cartao_dialog

LAST_ACCESS_FILE = os.path.join(faces_dir, "last_access.json")
STATUS_FILE = os.path.join(faces_dir, "status.json")


def load_last_access():
    if os.path.exists(LAST_ACCESS_FILE):
        try:
            with open(LAST_ACCESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_last_access(data):
    try:
        with open(LAST_ACCESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[ERRO] Não foi possível salvar last_access:", e)


def load_status():
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_status(data):
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[ERRO] Não foi possível salvar status:", e)


class UserDialog(QDialog):
    def __init__(self, name, img_path, last_access, status, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detalhes do Usuário")
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: #e2e8f0; }
            QLabel { font-size: 14px; }
            QPushButton { background-color: #2563eb; color: #fff; border-radius: 6px; padding: 6px 10px; }
        """)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        if os.path.exists(img_path):
            pixmap = QPixmap(img_path).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_label = QLabel()
            img_label.setPixmap(pixmap)
            img_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(img_label)

        name_label = QLabel(f"👤 {os.path.splitext(name)[0]}")
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(name_label)

        last_access_label = QLabel(f"🕒 Último acesso: {last_access if last_access else 'Nunca'}")
        last_access_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(last_access_label)

        status_label = QLabel(f"📍 Status: {'Dentro da empresa' if status == 'dentro' else 'Fora da empresa'}")
        status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.setLayout(layout)


class App(QWidget):
    def __init__(self, arduino):
        super().__init__()
        self.arduino = arduino
        self.setWindowTitle("Controle de Acesso RFID + Rosto")
        self.setGeometry(400, 200, 1000, 600)
        self.logs_visible = False
        self.last_access = load_last_access()
        self.status = load_status()

        # estilo
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
            }
            QLabel#title {
                font-size: 28px;
                font-weight: bold;
                color: #38bdf8;
                margin: 20px;
            }
            QPushButton {
                background-color: #1e293b;
                border: 2px solid #334155;
                border-radius: 10px;
                padding: 10px 16px;
                font-size: 15px;
                font-weight: bold;
                color: #e2e8f0;
            }
            QPushButton:hover {
                background-color: #2563eb;
                border: 2px solid #1d4ed8;
            }
            QLineEdit {
                background-color: #1e293b;
                border: 2px solid #334155;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                color: #e2e8f0;
            }
            QListWidget {
                background-color: #1e293b;
                border-radius: 8px;
                padding: 5px;
                font-size: 15px;
            }
            QTextEdit {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 2px solid #334155;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }
        """)

        # layout principal
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)

        self.label = QLabel("🔒 Controle de Acesso")
        self.label.setObjectName("title")
        self.label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.label)

        # botões
        btn_layout = QHBoxLayout()
        btn_unlock = QPushButton("Desbloquear")
        btn_unlock.clicked.connect(self.unlock)
        btn_layout.addWidget(btn_unlock)

        btn_add_face = QPushButton("Adicionar Rosto + Cartão")
        btn_add_face.clicked.connect(self.add_face)
        btn_layout.addWidget(btn_add_face)

        btn_remove_face = QPushButton("Remover Rosto")
        btn_remove_face.clicked.connect(self.remove_face)
        btn_layout.addWidget(btn_remove_face)

        btn_logs = QPushButton("Mostrar/Ocultar Logs")
        btn_logs.clicked.connect(self.toggle_logs)
        btn_layout.addWidget(btn_logs)

        left_layout.addLayout(btn_layout)

        # pesquisa
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Pesquisar usuário...")
        self.search_box.textChanged.connect(self.filter_users)
        left_layout.addWidget(self.search_box)

        # lista (escalável)
        self.user_list = QListWidget()
        self.user_list.itemClicked.connect(self.show_user_details)
        left_layout.addWidget(self.user_list)

        main_layout.addLayout(left_layout)

        # painel de logs lateral
        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        self.log_panel.setFixedWidth(300)
        self.log_panel.hide()
        main_layout.addWidget(self.log_panel)

        self.setLayout(main_layout)

        # dados
        self.known_encodings, self.known_names = load_known_faces()
        self.refresh_user_list()

    # mostrar/ocultar logs
    def toggle_logs(self):
        self.logs_visible = not self.logs_visible
        self.log_panel.setVisible(self.logs_visible)

    # atualizar lista
    def refresh_user_list(self):
        self.user_list.clear()
        for name in self.known_names:
            display = os.path.splitext(name)[0]
            item = QListWidgetItem(display)
            self.user_list.addItem(item)

    # filtrar
    def filter_users(self, text):
        for i in range(self.user_list.count()):
            item = self.user_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    # mostrar detalhes
    def show_user_details(self, item):
        display_name = item.text()
        matched = None
        for fname in self.known_names:
            if os.path.splitext(fname)[0] == display_name:
                matched = fname
                break
        if not matched:
            QMessageBox.warning(self, "Erro", "Arquivo do usuário não encontrado.")
            return
        img_path = os.path.join(faces_dir, matched)
        last = self.last_access.get(matched, self.last_access.get(os.path.splitext(matched)[0], "Nunca"))
        status = self.status.get(matched, "fora")
        dlg = UserDialog(matched, img_path, last, status, self)
        dlg.exec_()

    # adicionar log
    def add_log(self, message):
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.log_panel.append(f"[{timestamp}] {message}")

    # desbloquear
    def unlock(self):
        dialog = CaptureDialog()
        if dialog.exec_() != dialog.Accepted:
            return

        frame = dialog.captured_frame
        encoding = get_face_encoding(frame)
        if encoding is None:
            QMessageBox.warning(self, "Falha", "Nenhum rosto detectado.")
            return

        user_name = compare_faces(self.known_encodings, self.known_names, encoding)
        if not user_name:
            QMessageBox.warning(self, "Falha", "Rosto não reconhecido.")
            return

        display_name = os.path.splitext(user_name)[0]
        cards = load_cards()

        uid = aguardar_cartao_dialog(self, self.arduino, f"Rosto reconhecido: {display_name}\nAproxime o cartão do leitor")
        if not uid:
            QMessageBox.warning(self, "Falha", "Nenhum cartão detectado.")
            return

        if user_name in cards:
            expected_uid = cards[user_name]
            if expected_uid == uid:
                if self.arduino:
                    self.arduino.write(b"OPEN\n")

                current_status = self.status.get(user_name, "fora")
                if current_status == "fora":
                    action = "ENTRADA"
                    self.status[user_name] = "dentro"
                else:
                    action = "SAÍDA"
                    self.status[user_name] = "fora"

                QMessageBox.information(self, "Sucesso", f"{action} registrada para {display_name}")
                self.add_log(f"{action} de {display_name}")

                self.last_access[user_name] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                save_last_access(self.last_access)
                save_status(self.status)
            else:
                QMessageBox.critical(self, "Erro", "Cartão não corresponde ao rosto! Ação negada.")
                self.add_log(f"Tentativa com cartão inválido para {display_name} (UID detectado: {uid}, esperado: {expected_uid})")
            return

        reply = QMessageBox.question(
            self, "Registrar Cartão",
            f"Nenhum cartão cadastrado para {display_name}.\nDeseja registrar o cartão detectado para este usuário?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            QMessageBox.information(self, "Cancelado", "Registro de cartão cancelado.")
            return

        existing_owner = None
        for k, v in cards.items():
            if v == uid:
                existing_owner = k
                break
        if existing_owner:
            owner_display = os.path.splitext(existing_owner)[0]
            QMessageBox.critical(self, "Erro", f"Este cartão (UID {uid}) já está associado ao usuário '{owner_display}'.")
            self.add_log(f"Tentativa de registrar cartão já associado (UID {uid}) para {display_name}; proprietário: {owner_display}")
            return

        cards[user_name] = uid
        save_cards(cards)
        QMessageBox.information(self, "Sucesso", f"Cartão registrado e ENTRADA registrada para {display_name}")
        self.add_log(f"Cartão registrado e ENTRADA de {display_name} (UID: {uid})")
        if self.arduino:
            self.arduino.write(b"OPEN\n")

        self.last_access[user_name] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.status[user_name] = "dentro"
        save_last_access(self.last_access)
        save_status(self.status)

    # remover rosto
    def remove_face(self):
        item = self.user_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Erro", "Selecione um usuário para remover.")
            return

        user = item.text()
        fname = None
        for name in self.known_names:
            if os.path.splitext(name)[0] == user:
                fname = name
                break
        if not fname:
            QMessageBox.warning(self, "Erro", "Arquivo do usuário não encontrado.")
            return

        reply = QMessageBox.question(self, "Confirmação", f"Tem certeza que deseja remover {user}?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        try:
            os.remove(os.path.join(faces_dir, fname))
            self.known_names.remove(fname)
            self.known_encodings = [enc for enc, n in zip(self.known_encodings, self.known_names) if n != fname]
            save_known_faces(self.known_encodings, self.known_names)
            self.refresh_user_list()
            self.add_log(f"Usuário removido: {user}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao remover: {e}")

    # adicionar rosto
    def add_face(self):
        dialog = CaptureDialog()
        if dialog.exec_() != dialog.Accepted:
            return

        frame = dialog.captured_frame
        encoding = get_face_encoding(frame)
        if encoding is None:
            QMessageBox.warning(self, "Erro", "Nenhum rosto detectado.")
            return

        name, ok = QInputDialog.getText(self, "Novo Usuário", "Digite o nome do usuário:")
        if not ok or not name.strip():
            return
        name = name.strip() + ".png"

        img_path = os.path.join(faces_dir, name)
        cv2.imwrite(img_path, frame)

        self.known_encodings.append(encoding)
        self.known_names.append(name)
        save_known_faces(self.known_encodings, self.known_names)
        self.refresh_user_list()

        uid = aguardar_cartao_dialog(self, self.arduino, f"Associe um cartão ao usuário {os.path.splitext(name)[0]}")
        if not uid:
            QMessageBox.warning(self, "Erro", "Nenhum cartão detectado. O usuário foi cadastrado sem cartão.")
            return

        cards = load_cards()
        if uid in cards.values():
            QMessageBox.critical(self, "Erro", f"Este cartão já está associado a outro usuário.")
            return

        cards[name] = uid
        save_cards(cards)
        self.add_log(f"Usuário {os.path.splitext(name)[0]} registrado (UID: {uid})")
