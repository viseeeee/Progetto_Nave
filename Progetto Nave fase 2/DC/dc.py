# dc.py
import json
import socket
import time
import sys
import os

# Importa il modulo misurazione per simulare temperatura e umidità.
import misurazione

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "configurazionedc.conf"


def recv_line(sock: socket.socket) -> str:
    data = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("Connessione chiusa dal server")
        if chunk == b"\n":
            break
        data.extend(chunk)
    return data.decode("utf-8", errors="replace").strip()


def main():
    # 1) Leggo configurazione DC
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        configurazione = json.load(f)

    ip_server = configurazione["IPServer"]
    porta_server = int(configurazione["portaServer"])

    # 2) Connessione al DA
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip_server, porta_server))

        # 3) Ricevo parametri iniziali dal DA (1 riga JSON + \n)
        #    Esempio atteso: {"TEMPO_RILEVAZIONE":5,"N_DECIMALI":2}\n
        parametri_iniziali_str = recv_line(s)
        try:
            parametri_iniziali = json.loads(parametri_iniziali_str)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Messaggio iniziale non JSON dal DA: {parametri_iniziali_str!r}"
            ) from e

        tempo_rilevazione = int(parametri_iniziali["TEMPO_RILEVAZIONE"])
        n_decimali = int(parametri_iniziali["N_DECIMALI"])

        seriale = 0
        while True:
            seriale += 1

            # 4) Misuro (simulazione)
            temperatura = misurazione.on_temperatura(n_decimali)
            umidita = misurazione.on_umidita(n_decimali)

            # 5) Costruisco DatoIoT da inviare al DA
            dato_iot = {
                "cabina": configurazione["cabina"],
                "ponte": configurazione["ponte"],
                "sensore": configurazione["sensore"],
                "identita": configurazione["identita"],
                "osservazione": {
                    "rilevazione": seriale,
                    "temperatura": temperatura,
                    "umidita": umidita
                }
            }

            # Invio 1 riga JSON (no indent) + \n
            dato_iot_json = json.dumps(dato_iot, separators=(",", ":"))
            s.sendall((dato_iot_json + "\n").encode("utf-8"))

            # DEBUG (a schermo bello)
            print(json.dumps(dato_iot, indent=4, ensure_ascii=False))

            time.sleep(tempo_rilevazione)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDC terminato da tastiera.")
        sys.exit(0)