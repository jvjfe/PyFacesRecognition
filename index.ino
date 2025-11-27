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

void setup()
{
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

void loop()
{
    if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial())
    {
        String uid = "";
        for (byte i = 0; i < rfid.uid.size; i++)
        {
            if (rfid.uid.uidByte[i] < 0x10)
                uid += "0";
            uid += String(rfid.uid.uidByte[i], HEX);
        }
        uid.toUpperCase();

        Serial.println(uid); // envia UID para o Python

        rfid.PICC_HaltA();
        rfid.PCD_StopCrypto1();
        delay(200);
    }

    if (Serial.available() > 0)
    {
        String comando = Serial.readStringUntil('\n');
        comando.trim();
        if (comando.equals("OPEN"))
        {
            Serial.println("[DEBUG] Comando OPEN recebido");
            acessoAutorizado();
        }
        else if (comando.startsWith("LOG"))
        {
            Serial.println("Log recebido: " + comando);
        }
        else
        {
            Serial.print("[DEBUG] Comando desconhecido: ");
            Serial.println(comando);
        }
    }
}

void acessoAutorizado()
{
    digitalWrite(BUZZER, HIGH);
    delay(150);
    digitalWrite(BUZZER, LOW);

    piscarLED(3, 200);

    servoMotor.write(90);
    Serial.println("[DEBUG] Porta aberta");

    delay(3000);

    digitalWrite(BUZZER, HIGH);
    delay(300);
    digitalWrite(BUZZER, LOW);

    servoMotor.write(0); 
    Serial.println("[DEBUG] Porta fechada");
}

void piscarLED(int vezes, int intervalo)
{
    for (int i = 0; i < vezes; i++)
    {
        digitalWrite(LED_STATUS, HIGH);
        delay(intervalo);
        digitalWrite(LED_STATUS, LOW);
        delay(intervalo);
    }
}
