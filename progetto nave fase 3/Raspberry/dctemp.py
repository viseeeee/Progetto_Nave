import time
import sys
import json
import wifidc
import misurazione

CONFIG_FILE = "configurazionedc.json"

def main():
    # Connessione WiFi
    wlan = wifidc.connetti_wifi()
    time.sleep(1)
    wifidc.Info_WiFi(wlan)

    # Lettura configurazione sensore
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)

    pin = int(cfg["cablaggio"]["segnale"])
    tmin = cfg["sensore"]["tmin"]
    tmax = cfg["sensore"]["tmax"]
    umin = cfg["sensore"]["umin"]
    umax = cfg["sensore"]["umax"]

    # Parametri temporanei di test
    tempo_rilevazione = 5
    n_decimali = 1
    seriale = 0

    print("Avvio test sensore...")
    print("Pin:", pin)
    print("Intervallo lettura:", tempo_rilevazione, "secondi")
    print()

    while True:
        seriale += 1

        temperatura = misurazione.on_temperatura(pin, n_decimali, tmin, tmax)
        umidita = misurazione.on_umidita(pin, n_decimali, umin, umax)
        dataeora = int(time.time())

        dato_iot = {
            "camera": cfg["camera"],
            "ponte": cfg["ponte"],
            "sensore": cfg["sensore"],
            "identita": cfg["identita"],
            "osservazione": {
                "rilevazione": seriale,
                "dataeora": dataeora,
                "temperatura": temperatura,
                "umidita": umidita
            }
        }

        print(json.dumps(dato_iot))
        time.sleep(tempo_rilevazione)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
