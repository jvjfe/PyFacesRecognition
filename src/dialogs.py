import cv2, time, re
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QMessageBox
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer, QEventLoop

# --- Janela de pré-visualização ---
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

# --- Esperar cartão RFID ---
def aguardar_cartao_dialog(parent, arduino, message="Aproxime o cartão do leitor"):
    dialog = QMessageBox(parent)
    dialog.setWindowTitle("Aguardando Cartão")
    dialog.setText(message)
    dialog.setStandardButtons(QMessageBox.Cancel)
    dialog.setWindowModality(Qt.ApplicationModal)
    dialog.show()

    uid_container = {"uid": None}
    loop = QEventLoop()

    if arduino:
        try:
            arduino.reset_input_buffer()
            arduino.reset_output_buffer()
            time.sleep(0.05)
        except Exception:
            pass

    def check_serial():
        if arduino:
            try:
                while arduino.in_waiting > 0:
                    raw_line = arduino.readline().decode(errors="ignore").strip()
                    if not raw_line:
                        continue
                    m = re.search(r'([0-9A-Fa-f:\-\.]{4,})', raw_line)
                    if m:
                        uid_container["uid"] = m.group(1)
                        loop.quit()
                        return
            except Exception:
                loop.quit()

    cancel_button = dialog.button(QMessageBox.Cancel)
    cancel_button.clicked.connect(loop.quit)

    timer_serial = QTimer()
    timer_serial.timeout.connect(check_serial)
    timer_serial.start(50)

    loop.exec_()

    timer_serial.stop()
    dialog.close()

    return uid_container["uid"]
