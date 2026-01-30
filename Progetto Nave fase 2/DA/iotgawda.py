# iotgwda.py (DA/GIOT)
import json
import socket
import time
import sys
from pathlib import Path

import cripto  # la tua libreria finta di criptazione


BASE_DIR = Path(__file__).resolve().parent
PARAMETRI_FILE = BASE_DIR / "parametri.conf"

# Struttura progetto: .../DA, .../DC, .../IOTP
PROJECT_DIR = BASE_DIR.parent
IOTP_DIR = PROJECT_DIR / "IOTP"
IOTP_DB_FILE = IOTP_DIR / "iotdata.dbt"


def recv_line(sock: socket.socket) -> str:
    data = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            return ""  # connessione chiusa
        if chunk == b"\n":
            break
        data.extend(chunk)
    return data.decode("utf-8", errors="replace").strip()


def mean(values):
    return sum(values) / len(values) if values else None


def main():
    # 1) Leggo parametri del DA
    with open(PARAMETRI_FILE, "r", encoding="utf-8") as f:
        p = json.load(f)

    TEMPO_RILEVAZIONE = int(p["TEMPO_RILEVAZIONE"])
    N_DECIMALI = int(p["N_DECIMALI"])
    IDENTITA_GIOT = p["IDENTITA_GIOT"]
    TEMPO_INVIO_MIN = int(p["TEMPO_INVIO"])
    IP_SERVER = p["IP_SERVER"]
    PORTA_SERVER = int(p["PORTA_SERVER"])

    TEMPO_INVIO_SEC = TEMPO_INVIO_MIN * 60

    IOTP_DIR.mkdir(parents=True, exist_ok=True)

    # Buffer misure per DC (chiave = identita DC)
    # Valore: dict con metadata + liste di temperature/umidità
    buffer_dc = {}

    invionumero = 0
    last_send_ts = time.time()

    # 2) Avvio server TCP (non multithread)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((IP_SERVER, PORTA_SERVER))
        server.listen(5)

        print(f"DA in ascolto su {IP_SERVER}:{PORTA_SERVER}")
        print("CTRL+C per terminare.")

        try:
            while True:
                conn, addr = server.accept()
                with conn:
                    # 3) Invio parametri iniziali al DC (1 riga JSON + \n)
                    parametri_init = {
                        "TEMPO_RILEVAZIONE": TEMPO_RILEVAZIONE,
                        "N_DECIMALI": N_DECIMALI
                    }
                    conn.sendall((json.dumps(parametri_init) + "\n").encode("utf-8"))

                    # 4) Ricezione dati dal DC finché resta connesso
                    while True:
                        line = recv_line(conn)
                        if line == "":
                            break  # DC disconnesso

                        try:
                            dato_dc = json.loads(line)
                        except json.JSONDecodeError:
                            print(f"Ricevuto non-JSON: {line!r}")
                            continue

                        # DEBUG: dati ricevuti dal DC
                        print("Ricevuto da DC:")
                        print(json.dumps(dato_dc, indent=4, ensure_ascii=False))

                        identita_dc = dato_dc.get("identita", "UNKNOWN")
                        cabina = dato_dc.get("cabina")
                        ponte = dato_dc.get("ponte")

                        osservazione = dato_dc.get("osservazione", {})
                        t = osservazione.get("temperatura")
                        u = osservazione.get("umidita")

                        if identita_dc not in buffer_dc:
                            buffer_dc[identita_dc] = {
                                "cabina": cabina,
                                "ponte": ponte,
                                "temperatura": [],
                                "umidita": []
                            }

                        # Accumulo per medie
                        if isinstance(t, (int, float)):
                            buffer_dc[identita_dc]["temperatura"].append(t)
                        if isinstance(u, (int, float)):
                            buffer_dc[identita_dc]["umidita"].append(u)

                        # 5) Ogni TEMPO_INVIO minuti genero invio verso IOTP
                        now = time.time()
                        if now - last_send_ts >= TEMPO_INVIO_SEC:
                            invionumero += 1
                            last_send_ts = now

                            # Creo un invio per ogni DC visto finora
                            for dc_id, b in buffer_dc.items():
                                mt = mean(b["temperatura"])
                                mu = mean(b["umidita"])

                                # Se non ho dati, salto
                                if mt is None or mu is None:
                                    continue

                                dato_iotp = {
                                    "invionumero": invionumero,
                                    "cabina": b["cabina"],
                                    "ponte": b["ponte"],
                                    "temperatura": round(mt, N_DECIMALI),
                                    "umidita": round(mu, N_DECIMALI),
                                    "dateora": int(time.time()),
                                    "identita": IDENTITA_GIOT,
                                    "dc": dc_id
                                }

                                # Criptazione (finta) come da specifica (variabili separate)
                                dato_iot_dc_json = json.dumps(dato_iotp)
                                dato_iot_dc_json_criptato = cripto.criptazione(dato_iot_dc_json)

                                # DEBUG: stampo dato criptato “da inviare”
                                print("Da inviare a IOTPlatform (criptato):")
                                print(dato_iot_dc_json_criptato)

                                # Simulazione IoTPlatform: salvo NON criptato su file iotdata.dbt
                                with open(IOTP_DB_FILE, "a", encoding="utf-8") as out:
                                    out.write(dato_iot_dc_json + "\n")

                                # Azzero buffer dopo invio (medie per finestra TEMPO_INVIO)
                                b["temperatura"].clear()
                                b["umidita"].clear()

        except KeyboardInterrupt:
            print("\nTerminazione DA da tastiera.")
            print(f"Invii effettuati verso IoTPlatform: {invionumero}")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDC terminato da tastiera.")
        sys.exit(0)
