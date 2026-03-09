import socket
import time
import sys
import json
import wifidc
import misurazione

DA_FILE = "da.json"
CONFIG_FILE = "configurazionedc.json"

def recv_line(sock) -> str:
    data = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            raise OSError("Connessione chiusa dal server")
        if chunk == b"\n":
            break
        data.extend(chunk)
    return data.decode("utf-8", errors="replace").strip()

def connetti_socket(ip, porta, retry=5):
    for i in range(retry):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, porta))
            return s
        except OSError as e:
            print("Connessione fallita (" + str(i+1) + "/" + str(retry) + "): " + str(e))
            try:
                s.close()
            except:
                pass
            time.sleep(2)
    raise OSError("Impossibile connettersi al server")

def main():
    # Connessione WiFi
    wlan = wifidc.connetti_wifi()
    time.sleep(1)
    wifidc.Info_WiFi(wlan)

    # Configurazioni
    with open(DA_FILE, "r") as f:
        da = json.load(f)
    ip_server = da["IP"]
    porta_server = int(da["porta"])

    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
    pin = int(cfg["cablaggio"]["segnale"])
    tmin = cfg["sensore"]["tmin"]
    tmax = cfg["sensore"]["tmax"]
    umin = cfg["sensore"]["umin"]
    umax = cfg["sensore"]["umax"]

    # Apri socket con retry
    sock = connetti_socket(ip_server, porta_server)

    # Ricezione configurazione iniziale dal server
    init_str = recv_line(sock)
    init = json.loads(init_str)
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
            sock.send(payload.encode("utf-8"))
        except OSError as e:
            print("Invio fallito: " + str(e) + ", riconnessione socket...")
            try:
                sock.close()
            except:
                pass
            sock = connetti_socket(ip_server, porta_server)
            continue

        # Su MicroPython indent non e' supportato, stampa compatto
        print(payload)
        time.sleep(tempo_rilevazione)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
