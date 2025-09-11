````markdown
# Sistema de Reconhecimento Facial com RFID

Este projeto foi desenvolvido como **Trabalho de Conclusão de Curso (TCC) de Automação Industrial** com o objetivo de criar um sistema de **controle de acesso seguro** utilizando **reconhecimento facial** e autenticação com **cartão RFID**.  
Somente após a verificação da face e a aproximação de um cartão autorizado, o sistema libera o acesso através da abertura de uma porta controlada por um servo motor e indicações visuais com LED.

---

## Funcionalidades
- Reconhecimento facial automático via câmera.
- Validação de cartão RFID para autenticação do usuário.
- Controle físico de acesso com **servo motor** (porta).
- Indicação de status por **LED**.
- Integração entre **Python** (processamento da face) e **Arduino Uno** (controle físico).

---

## Peças Utilizadas
- **1x Arduino Uno**
- **1x Módulo RFID RC522**
- **1x Servo motor 5V**
- **1x LED (vermelho ou verde)**
- **1x Resistor 220 Ω**
- **Jumpers macho-fêmea**
- **Protoboard**

---

## 💻 Principais Bibliotecas Utilizadas

### Python
- `opencv-python` → Captura e processamento de imagem para reconhecimento facial.  
- `face-recognition` → Identificação e validação de rostos.  
- `pyserial` → Comunicação entre Python e Arduino.

### Arduino
- `SPI.h` → Comunicação com o módulo RFID.  
- `MFRC522.h` → Leitura e autenticação de cartões RFID.  
- `Servo.h` → Controle do servo motor.

---

## Como Ligar e Montar o Projeto

### Montagem do Circuito
1. **Módulo RFID RC522** conectado ao Arduino (padrão SPI):  
   - SDA → pino 10  
   - SCK → pino 13  
   - MOSI → pino 11  
   - MISO → pino 12  
   - RST → pino 9  
   - VCC → 3.3V  
   - GND → GND  

2. **Servo motor 5V**:  
   - Sinal (laranja/amarelo) → pino 3 do Arduino  
   - VCC (vermelho) → 5V  
   - GND (marrom/preto) → GND  

3. **LED + Resistor 220 Ω**:  
   - Anodo → pino 5 do Arduino (com resistor em série)  
   - Catodo → GND  

---
## Tecnologias e Bibliotecas Principais

### 🔹 Python
- [PyQt5](https://pypi.org/project/PyQt5/) → Interface gráfica  
- [face_recognition](https://github.com/ageitgey/face_recognition) → Reconhecimento facial  
- [OpenCV](https://opencv.org/) → Manipulação da câmera e imagens  
- [numpy](https://numpy.org/) → Operações matemáticas  
- [pickle](https://docs.python.org/3/library/pickle.html) → Persistência de dados (rostos e cartões)  
- [pyserial](https://pyserial.readthedocs.io/) → Comunicação serial com Arduino  

### 🔹 Arduino
- [MFRC522](https://github.com/miguelbalboa/rfid) → Leitura de cartões RFID  
- [Servo.h](https://www.arduino.cc/en/reference/servo) → Controle do motor de trava  
- [SPI.h](https://www.arduino.cc/en/reference/SPI) → Comunicação com módulo RFID  

---

## Como Executar

1. Clone o repositório:
   ```bash
   git clone https://github.com/jvjfe/PyFacesRecognition
   cd PyFacesRecognition
````

2. Ative o ambiente virtual e instale as dependências:

   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows

   pip install -r requirements.txt
   ```

3. Conecte o **Arduino Uno** via USB e carregue o código `arduino/index.ino`.

4. Execute o sistema Python:

   ```bash
   python index.py
   ```

5. O sistema iniciará a câmera.

   * Ao reconhecer o rosto, o LED pisca.
   * É necessário aproximar o cartão RFID autorizado.
   * Se válido, o servo motor abre a porta por alguns segundos.

---

# Autores

João Fernando Zanin de Andrade Fernandes
João Vítor Justino Ferri - [Jvjfe](https://github.com/jvjfe)
Josué Elias Guimarães Cruz
Lucas do Nascimento Feitosa Scarparo
Thiago Henrique Marques Magalhães Alcântara

Trabalho de Conclusão de Curso - ETEC Automação Industrial