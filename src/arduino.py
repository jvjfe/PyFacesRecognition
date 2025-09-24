import serial, serial.tools.list_ports, time

def conectar_arduino():
    for port in serial.tools.list_ports.comports():
        try:
            if "Arduino" in port.description or "USB" in port.description:
                arduino = serial.Serial(port.device, 9600, timeout=1)
                time.sleep(2)
                print(f"Conectado ao Arduino na porta {port.device}")
                return arduino
        except Exception as e:
            print("Erro ao tentar conectar:", e)
    print("Não foi possível detectar o Arduino. Certifique-se de que está conectado e a porta está correta.")
    return None
