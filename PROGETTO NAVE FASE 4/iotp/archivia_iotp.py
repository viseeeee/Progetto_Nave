import json
from pathlib import Path
import paho.mqtt.client as mqtt
import cripto

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "iotp.json"

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

TOPIC = config["topic"]
BROKER = config["broker"]["host"]
PORTA = int(config["broker"]["porta"])
DBFILE = BASE_DIR / config["dbfile"]["file"]
MODO = config["dbfile"]["modo"]


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connesso al broker MQTT")
        print(f"Sottoscritto al topic: {TOPIC}")
        client.subscribe(TOPIC)
    else:
        print(f"Errore connessione MQTT, codice: {rc}")


def on_message(client, userdata, msg):
    try:
        payload_criptato = msg.payload.decode("utf-8")
        payload_decriptato = cripto.decriptazione(payload_criptato)
        dato = json.loads(payload_decriptato)

        print("Dato ricevuto da iotgwda.py e decriptato:")
        print(json.dumps(dato, indent=4, ensure_ascii=False))

        with open(DBFILE, MODO, encoding="utf-8") as f:
            f.write(json.dumps(dato, ensure_ascii=False) + "\n")

    except Exception as e:
        print("Errore nella ricezione o archiviazione:", e)


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Connessione a broker {BROKER}:{PORTA} ...")
    client.connect(BROKER, PORTA, 60)
    client.loop_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSpegnimento manuale del Gateway in corso.")