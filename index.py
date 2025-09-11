import sys
import os
import cv2
import numpy as np
import face_recognition
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel,
    QFileDialog, QMessageBox, QScrollArea, QHBoxLayout, QFrame,
    QDialog, QDialogButtonBox, QInputDialog
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer, QEventLoop
import pickle
import serial
import serial.tools.list_ports
import time

# === Configurações ===
faces_dir = "faces"
os.makedirs(faces_dir, exist_ok=True)
encodings_file = os.path.join(faces_dir, "encodings.pkl")
cards_file = os.path.join(faces_dir, "cards.pkl")

# === Detectar e conectar ao Arduino automaticamente ===
arduino = None
for port in serial.tools.list_ports.comports():
    try:
        if "Arduino" in port.description or "USB" in port.description:
            arduino = serial.Serial(port.device, 9600, timeout=1)
            time.sleep(2)
            print(f"Conectado ao Arduino na porta {port.device}")
            break
    except Exception as e:
        print("Erro ao tentar conectar:", e)

if arduino is None:
    print("Não foi possível detectar o Arduino. Certifique-se de que está conectado e a porta está correta.")

# === Utilitários ===
def load_known_faces():
    encodings, names = [], []
    if os.path.exists(encodings_file):
        with open(encodings_file, "rb") as f:
            data = pickle.load(f)
            raw_encodings = data.get("encodings", [])
            raw_names = data.get("names", [])
            for e, n in zip(raw_encodings, raw_names):
                arr = np.array(e)
                if arr.shape == (128,):
                    encodings.append(arr)
                    names.append(n)
    return encodings, names

def save_known_faces(encodings, names):
    serializable_encodings = [e.tolist() for e in encodings]
    with open(encodings_file, "wb") as f:
        pickle.dump({"encodings": serializable_encodings, "names": names}, f)

def get_face_encoding(image):
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_image, model="hog")
    if not face_locations:
        return None
    encodings = face_recognition.face_encodings(rgb_image, known_face_locations=face_locations)
    return encodings[0] if encodings else None

def compare_faces(known_encodings, known_names, encoding, tolerance=0.5):
    if not known_encodings or encoding is None:
        return None
    known_encodings = [np.array(e) for e in known_encodings if np.array(e).shape == (128,)]
    encoding = np.array(encoding)
    if encoding.shape != (128,) or not known_encodings:
        return None
    results = face_recognition.compare_faces(known_encodings, encoding, tolerance=tolerance)
    if any(results):
        index = results.index(True)
        return known_names[index]
    return None

def load_cards():
    if os.path.exists(cards_file):
        with open(cards_file, "rb") as f:
            return pickle.load(f)
    return {}

def save_cards(cards):
    with open(cards_file, "wb") as f:
        pickle.dump(cards, f)

# === Ler UID do Arduino com caixa de espera (não bloqueia GUI) ===
def aguardar_cartao_dialog(parent, message="Aproxime o cartão do leitor"):
    dialog = QMessageBox(parent)
    dialog.setWindowTitle("Aguardando Cartão")
    dialog.setText(message)
    dialog.setStandardButtons(QMessageBox.Cancel)
    dialog.setWindowModality(Qt.ApplicationModal)
    dialog.show()

    uid_container = {"uid": None}
    loop = QEventLoop()

    def check_serial():
        if arduino:
            try:
                while arduino.in_waiting > 0:
                    line = arduino.readline().decode(errors="ignore").strip()
                    if line:
                        # Ignora mensagens de status e pega só UID válido
                        if line.startswith("Arduino pronto") or line.lower().startswith("log"):
                            print(f"[DEBUG] Mensagem ignorada do Arduino: {line}")
                        else:
                            print(f"[DEBUG] UID recebido: {line}")
                            uid_container["uid"] = line
                            loop.quit()
                            return
            except Exception as e:
                print("[ERROR] Erro lendo Arduino:", e)
                loop.quit()

    def close_dialog():
        print("[DEBUG] Usuário fechou a espera do cartão")
        loop.quit()

    # Conecta botão de fechar
    cancel_button = dialog.button(QMessageBox.Cancel)
    cancel_button.clicked.connect(close_dialog)

    # Timer para checagem do Arduino
    timer_serial = QTimer()
    timer_serial.timeout.connect(check_serial)
    timer_serial.start(50)  # checa a cada 50ms

    loop.exec_()

    timer_serial.stop()
    dialog.close()

    if uid_container["uid"] is None:
        print("[DEBUG] Nenhum UID detectado")
    else:
        print(f"[DEBUG] UID final retornado: {uid_container['uid']}")

    return uid_container["uid"]

# === Janela de pré-visualização ===
class CaptureDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pré-visualização do Rosto")
        self.setGeometry(500, 250, 640, 480)

        layout = QVBoxLayout()
        self.label = QLabel("Iniciando câmera...")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        self.captured_frame = None

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            self.captured_frame = frame
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(qimg).scaled(600, 400, Qt.KeepAspectRatio))

    def accept(self):
        if self.captured_frame is None:
            QMessageBox.warning(self, "Erro", "Nenhum frame capturado.")
            return
        self.timer.stop()
        self.cap.release()
        super().accept()

    def reject(self):
        self.timer.stop()
        self.cap.release()
        super().reject()

# === Interface Principal ===
class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Controle de Acesso RFID + Rosto")
        self.setGeometry(400, 200, 750, 600)
        self.setStyleSheet("background-color: #ecf0f1;")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        self.label = QLabel("🔒 Controle de Acesso")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 26px; font-weight: bold; color: #2c3e50; margin: 15px;")
        layout.addWidget(self.label)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_style = "font-size: 18px; padding: 14px 20px; border-radius: 10px; color: white;"

        btn_unlock = QPushButton("Desbloquear")
        btn_unlock.setStyleSheet(f"background-color: #3498db; {btn_style}")
        btn_unlock.clicked.connect(self.unlock)
        btn_layout.addWidget(btn_unlock)

        btn_add_face = QPushButton("Adicionar Rosto + Cartão")
        btn_add_face.setStyleSheet(f"background-color: #2ecc71; {btn_style}")
        btn_add_face.clicked.connect(self.add_face)
        btn_layout.addWidget(btn_add_face)

        btn_remove_face = QPushButton("Remover Rosto")
        btn_remove_face.setStyleSheet(f"background-color: #e74c3c; {btn_style}")
        btn_remove_face.clicked.connect(self.remove_face)
        btn_layout.addWidget(btn_remove_face)

        layout.addLayout(btn_layout)

        self.users_label = QLabel("Usuários cadastrados:")
        self.users_label.setStyleSheet("font-size: 18px; margin-top: 20px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(self.users_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.users_container = QVBoxLayout()
        self.users_container.setAlignment(Qt.AlignTop)

        users_widget = QWidget()
        users_widget.setLayout(self.users_container)
        self.scroll_area.setWidget(users_widget)
        layout.addWidget(self.scroll_area)

        self.setLayout(layout)

        self.known_encodings, self.known_names = load_known_faces()
        self.refresh_user_list()

    # === Atualiza a lista de usuários ===
    def refresh_user_list(self):
        for i in reversed(range(self.users_container.count())):
            widget = self.users_container.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        for name in self.known_names:
            user_frame = QFrame()
            user_frame.setStyleSheet("background-color: white; border: 1px solid #ddd; border-radius: 8px; margin: 5px; padding: 8px;")
            user_layout = QHBoxLayout()

            img_path = os.path.join(faces_dir, name)
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_label = QLabel()
                img_label.setPixmap(pixmap)
                user_layout.addWidget(img_label)

            display_name = os.path.splitext(name)[0]
            name_label = QLabel(display_name)
            name_label.setStyleSheet("font-size: 15px; margin-left: 10px; color: #2c3e50;")
            user_layout.addWidget(name_label)

            user_frame.setLayout(user_layout)
            self.users_container.addWidget(user_frame)

    # === Desbloquear porta com rosto e cartão ===
    def unlock(self):
        dialog = CaptureDialog()
        if dialog.exec_() != QDialog.Accepted:
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

        # Aguarda cartão de forma não bloqueante
        uid = aguardar_cartao_dialog(self, f"Rosto reconhecido: {display_name}\nAproxime o cartão do leitor")
        if not uid:
            QMessageBox.warning(self, "Falha", "Nenhum cartão detectado.")
            return

        if user_name in cards and cards[user_name] == uid:
            if arduino:
                arduino.write(b"OPEN\n")
            QMessageBox.information(self, "Sucesso", f"Acesso liberado para {display_name}")
        elif user_name in cards and cards[user_name] != uid:
            QMessageBox.critical(self, "Erro", "Cartão não corresponde ao rosto!")
        else:
            cards[user_name] = uid
            save_cards(cards)
            if arduino:
                arduino.write(b"OPEN\n")
            QMessageBox.information(self, "Sucesso", f"Cartão registrado e acesso liberado para {display_name}")

    # === Adicionar rosto + cartão ===
    def add_face(self):
        dialog = CaptureDialog()
        if dialog.exec_() != QDialog.Accepted:
            return

        frame = dialog.captured_frame
        encoding = get_face_encoding(frame)
        if encoding is None:
            QMessageBox.warning(self, "Falha", "Nenhum rosto detectado.")
            return

        name, _ = QFileDialog.getSaveFileName(self, "Salvar rosto", faces_dir + "/", "Imagem (*.jpg)")
        if not name:
            return

        uid = aguardar_cartao_dialog(self, "Aproxime o cartão para associar ao usuário")
        if not uid:
            QMessageBox.warning(self, "Falha", "Nenhum cartão detectado. Cadastro cancelado.")
            return

        cards = load_cards()
        base_name = os.path.basename(name)
        if base_name in self.known_names:
            QMessageBox.warning(self, "Erro", "Esse usuário já está cadastrado. Remova antes de adicionar novamente.")
            return


        cv2.imwrite(name, frame)
        self.known_encodings.append(np.array(encoding))
        self.known_names.append(os.path.basename(name))
        save_known_faces(self.known_encodings, self.known_names)

        cards[os.path.basename(name)] = uid
        save_cards(cards)

        self.refresh_user_list()
        QMessageBox.information(self, "Sucesso", f"Rosto e cartão cadastrados para {os.path.splitext(os.path.basename(name))[0]}")

    # === Remover rosto ===
    def remove_face(self):
        if not self.known_names:
            QMessageBox.warning(self, "Erro", "Nenhum rosto para remover.")
            return

        # Mostra lista de usuários para escolher
        user, ok = QInputDialog.getItem(self, "Remover rosto", "Selecione o usuário:", self.known_names, 0, False)
        if ok and user:
            index = self.known_names.index(user)
            removed_name = self.known_names.pop(index)
            self.known_encodings.pop(index)

            # Remove imagem do usuário
            img_path = os.path.join(faces_dir, removed_name)
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except Exception as e:
                    print(f"[ERRO] Não foi possível remover a imagem {img_path}: {e}")

            # Remove também do cards.pkl
            cards = load_cards()
            if removed_name in cards:
                del cards[removed_name]
            save_cards(cards)

            # Atualiza encodings.pkl
            save_known_faces(self.known_encodings, self.known_names)

            # Atualiza lista na interface
            self.refresh_user_list()
            QMessageBox.information(self, "Sucesso", f"Usuário removido: {os.path.splitext(removed_name)[0]}")

# === Executar app ===
app = QApplication(sys.argv)
app.setStyle("Fusion")
app.setStyleSheet("""
    QWidget {
        background-color: #ffffff;
        color: #2c3e50;
    }
    QPushButton {
        border-radius: 8px;
        padding: 10px;
        font-size: 16px;
    }
    QLabel {
        color: #2c3e50;
    }
""")

window = App()
window.show()
sys.exit(app.exec_())
