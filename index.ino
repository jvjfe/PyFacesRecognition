#include <SPI.h>
#include <MFRC522.h>
#include <Servo.h>

#define RST_PIN 9
#define SS_PIN 10
#define SERVO_PIN 3
#define LED_STATUS 5
#define BUZZER 7

Servo servoMotor;
MFRC522 rfid(SS_PIN, RST_PIN);

void somUrnaConfirmacao() {
    tone(BUZZER, 2132, 60);
    delay(80);
    tone(BUZZER, 2032, 60);
    delay(80);
    tone(BUZZER, 2132, 200); 
    delay(250);
    noTone(BUZZER);
}


void somUrnaFechando() {
    tone(BUZZER, 988, 120);
    delay(150)
    noTone(BUZZER);
}

void setup() {
    Serial.begin(9600);
    SPI.begin();
    rfid.PCD_Init();

    servoMotor.attach(SERVO_PIN);
    servoMotor.write(0);

    pinMode(LED_STATUS, OUTPUT);
    digitalWrite(LED_STATUS, LOW);

    pinMode(BUZZER, OUTPUT);
    digitalWrite(BUZZER, LOW);

    Serial.println("Arduino pronto para receber comandos...");
}

void loop() {
    if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
        String uid = "";
        for (byte i = 0; i < rfid.uid.size; i++) {
            if (rfid.uid.uidByte[i] < 0x10)
                uid += "0";
            uid += String(rfid.uid.uidByte[i], HEX);
        }
        uid.toUpperCase();

        Serial.println(uid);

        rfid.PICC_HaltA();
        rfid.PCD_StopCrypto1();
        delay(200);
    }

    if (Serial.available() > 0) {
        String comando = Serial.readStringUntil('\n');
        comando.trim();
        if (comando.equals("OPEN")) {
            Serial.println("[DEBUG] Comando OPEN recebido");
            acessoAutorizado();
        } else if (comando.startsWith("LOG")) {
            Serial.println("Log recebido: " + comando);
        } else {
            Serial.print("[DEBUG] Comando desconhecido: ");
            Serial.println(comando);
        }
    }
}

void acessoAutorizado() {
    somUrnaConfirmacao();

    piscarLED(3, 200);

    servoMotor.write(90);
    Serial.println("[DEBUG] Porta aberta");

    delay(3000);

    somUrnaFechando();

    servoMotor.write(0);
    Serial.println("[DEBUG] Porta fechada");
}

void piscarLED(int vezes, int intervalo) {
    for (int i = 0; i < vezes; i++) {
        digitalWrite(LED_STATUS, HIGH);
        delay(intervalo);
        digitalWrite(LED_STATUS, LOW);
        delay(intervalo);
    }
}
