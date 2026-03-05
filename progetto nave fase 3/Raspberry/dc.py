import socket
import time
import os
import sys
import json  

import wifidc
import misurazione

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DA_FILE = os.path.join(BASE_DIR, "da.json")
CONFIG_FILE = os.path.join(BASE_DIR, "configurazionedc.json")

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
    
    wlan = wifidc.connetti_wifi()  
    print(wifidc.info(wlan))  

   
    with open(DA_FILE, "r", encoding="utf-8") as f:
        da = json.load(f)
    ip_server = da["IP"]
    porta_server = int(da["porta"])

    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    pin = int(cfg["cablaggio"]["segnale"])
    tmin = cfg["sensore"]["tmin"]
    tmax = cfg["sensore"]["tmax"]
    umin = cfg["sensore"]["umin"]
    umax = cfg["sensore"]["umax"]

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip_server, porta_server))

        init_str = recv_line(sock)
        try:
            init = json.loads(init_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Messaggio iniziale non JSON dal DA: {init_str!r}") from e

        tempo_rilevazione = int(init["TEMPO_RILEVAZIONE"])
        n_decimali = int(init["N_DECIMALI"])

        seriale = 0
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

            payload = json.dumps(dato_iot, separators=(",", ":"), ensure_ascii=False) + "\n"
            try:
                sock.sendall(payload.encode("utf-8"))
            except (ConnectionError, OSError) as e:
                print(f"Invio fallito: {e}")
                break

            print(json.dumps(dato_iot, indent=4, ensure_ascii=False))
            time.sleep(tempo_rilevazione)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
