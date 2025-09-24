# ui.py
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


class UserDialog(QDialog):
    def __init__(self, name, img_path, last_access, parent=None):
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

        # estilo (removida a fonte específica para evitar warnings no mac)
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
        # procura a file name correspondente em known_names
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
        dlg = UserDialog(matched, img_path, last, self)
        dlg.exec_()

    # adicionar log
    def add_log(self, message):
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.log_panel.append(f"[{timestamp}] {message}")

    # desbloquear (corrigido para NÃO cadastrar automaticamente um cartão diferente)
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

        # Caso 1: usuário já tem um cartão cadastrado
        if user_name in cards:
            expected_uid = cards[user_name]
            if expected_uid == uid:
                # acesso autorizado
                if self.arduino:
                    self.arduino.write(b"OPEN\n")
                QMessageBox.information(self, "Sucesso", f"Acesso liberado para {display_name}")
                self.add_log(f"Acesso liberado para {display_name}")
                # registrar último acesso usando a chave exata (com extensão)
                self.last_access[user_name] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                save_last_access(self.last_access)
            else:
                # CARTÃO DIFERENTE: negar e LOGAR tentativa — NÃO sobrescrever
                QMessageBox.critical(self, "Erro", "Cartão não corresponde ao rosto! Ação negada.")
                self.add_log(f"Tentativa com cartão inválido para {display_name} (UID detectado: {uid}, esperado: {expected_uid})")
            return

        # Caso 2: usuário NÃO tem cartão cadastrado — perguntar se deseja registrar
        reply = QMessageBox.question(
            self, "Registrar Cartão",
            f"Nenhum cartão cadastrado para {display_name}.\nDeseja registrar o cartão detectado para este usuário?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            QMessageBox.information(self, "Cancelado", "Registro de cartão cancelado.")
            return

        # Antes de registrar, checar se o UID já pertence a outro usuário
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

        # Tudo ok: registrar o cartão para user_name
        cards[user_name] = uid
        save_cards(cards)
        QMessageBox.information(self, "Sucesso", f"Cartão registrado e acesso liberado para {display_name}")
        self.add_log(f"Cartão registrado para {display_name} (UID: {uid})")
        if self.arduino:
            self.arduino.write(b"OPEN\n")
        self.last_access[user_name] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        save_last_access(self.last_access)

    # adicionar rosto
    def add_face(self):
        dialog = CaptureDialog()
        if dialog.exec_() != dialog.Accepted:
            return

        frame = dialog.captured_frame
        encoding = get_face_encoding(frame)
        if encoding is None:
            QMessageBox.warning(self, "Falha", "Nenhum rosto detectado.")
            return

        name, _ = QFileDialog.getSaveFileName(self, "Salvar rosto", faces_dir + "/", "Imagem (*.jpg)")
        if not name:
            return

        base = os.path.basename(name)
        # previne cadastrar mesmo nome duas vezes
        if base in self.known_names:
            QMessageBox.warning(self, "Erro", "Já existe um usuário com esse nome. Use outro nome ou remova o existente.")
            return

        uid = aguardar_cartao_dialog(self, self.arduino, "Aproxime o cartão para associar ao usuário")
        if not uid:
            QMessageBox.warning(self, "Falha", "Nenhum cartão detectado. Cadastro cancelado.")
            return

        # checa se o UID já pertence a outro usuário
        cards = load_cards()
        for owner, assigned_uid in cards.items():
            if assigned_uid == uid:
                owner_display = os.path.splitext(owner)[0]
                QMessageBox.critical(self, "Erro", f"Este cartão já está associado ao usuário '{owner_display}'. Cadastro cancelado.")
                return

        # salva imagem e registra
        cv2.imwrite(name, frame)
        self.known_encodings.append(np.array(encoding))
        self.known_names.append(base)
        save_known_faces(self.known_encodings, self.known_names)

        cards[base] = uid
        save_cards(cards)

        self.refresh_user_list()
        self.add_log(f"Rosto e cartão cadastrados para {base}")

    # remover rosto (mantive sua lógica segura)
    def remove_face(self):
        # tenta usar seleção atual da QListWidget
        selected_item = self.user_list.currentItem() if hasattr(self, "user_list") else None

        if selected_item:
            display_name = selected_item.text()
            reply = QMessageBox.question(
                self, "Confirmar Remoção",
                f"Remover usuário '{display_name}' ?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            # encontra o filename correspondente em self.known_names
            matched_index = None
            matched_fname = None
            for i, fname in enumerate(self.known_names):
                if os.path.splitext(fname)[0] == display_name:
                    matched_index = i
                    matched_fname = fname
                    break

            if matched_index is None:
                QMessageBox.warning(self, "Erro", "Usuário não encontrado nos registros.")
                return

            # remove encoding e nome
            removed_name = self.known_names.pop(matched_index)
            try:
                self.known_encodings.pop(matched_index)
            except Exception:
                pass

            # remove arquivo de imagem (se existir)
            img_path = os.path.join(faces_dir, removed_name)
            try:
                if os.path.exists(img_path):
                    os.remove(img_path)
            except Exception as e:
                print(f"[ERRO] Não foi possível remover imagem {img_path}: {e}")

            # remove do cards.pkl (tenta com nome com e sem extensão)
            cards = load_cards()
            if removed_name in cards:
                del cards[removed_name]
            key_no_ext = os.path.splitext(removed_name)[0]
            if key_no_ext in cards:
                del cards[key_no_ext]
            save_cards(cards)

            # remove do last_access se existir (com e sem extensão)
            if removed_name in self.last_access:
                del self.last_access[removed_name]
            if key_no_ext in self.last_access:
                del self.last_access[key_no_ext]
            save_last_access(self.last_access)

            # salva encodings novamente
            save_known_faces(self.known_encodings, self.known_names)

            # atualiza UI
            self.refresh_user_list()
            self.add_log(f"Usuário removido: {removed_name}")
            return

        # fallback: lista vazia ou sem seleção -> mostra uma caixa para escolher
        names_display = [os.path.splitext(n)[0] for n in self.known_names]
        if not names_display:
            QMessageBox.information(self, "Info", "Nenhum usuário cadastrado.")
            return
        user, ok = QInputDialog.getItem(self, "Remover rosto", "Selecione o usuário:", names_display, 0, False)
        if not ok or not user:
            return

        # reutiliza a lógica acima para remover
        # encontra index
        matched_index = None
        matched_fname = None
        for i, fname in enumerate(self.known_names):
            if os.path.splitext(fname)[0] == user:
                matched_index = i
                matched_fname = fname
                break
        if matched_index is None:
            QMessageBox.warning(self, "Erro", "Usuário não encontrado.")
            return

        removed_name = self.known_names.pop(matched_index)
        try:
            self.known_encodings.pop(matched_index)
        except Exception:
            pass

        img_path = os.path.join(faces_dir, removed_name)
        try:
            if os.path.exists(img_path):
                os.remove(img_path)
        except Exception as e:
            print(f"[ERRO] Não foi possível remover imagem {img_path}: {e}")

        cards = load_cards()
        if removed_name in cards:
            del cards[removed_name]
        key_no_ext = os.path.splitext(removed_name)[0]
        if key_no_ext in cards:
            del cards[key_no_ext]
        save_cards(cards)

        if removed_name in self.last_access:
            del self.last_access[removed_name]
        if key_no_ext in self.last_access:
            del self.last_access[key_no_ext]
        save_last_access(self.last_access)

        save_known_faces(self.known_encodings, self.known_names)
        self.refresh_user_list()
        self.add_log(f"Usuário removido: {removed_name}")
