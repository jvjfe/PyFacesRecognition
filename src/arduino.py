# arduino.py
import serial
import serial.tools.list_ports
import time

def conectar_arduino():
    for port in serial.tools.list_ports.comports():
        try:
            if "Arduino" in port.description or "USB" in port.description:
                arduino = serial.Serial(port.device, 9600, timeout=1)
                time.sleep(2)
                print(f"✅ Conectado ao Arduino na porta {port.device}")
                return arduino
        except Exception as e:
            print("Erro ao tentar conectar:", e)
    return None
