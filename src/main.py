import sys
from PyQt5.QtWidgets import QApplication

from .arduino import conectar_arduino
from .ui import App

def main():
    app = QApplication(sys.argv)
    arduino = conectar_arduino()
    window = App(arduino)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
