# iotgwda.py (DA/GIOT)
import json
import socket
import time
import sys
from pathlib import Path

# Importa il modulo di criptazione (modulo locale richiesto) [cite: 278]
import cripto 

# Percorsi come da specifiche 
BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "configurazione"
PARAMETRI_FILE = CONFIG_DIR / "parametri.json" # 

IOTP_DIR = BASE_DIR / "iotp"
IOTP_DB_FILE = IOTP_DIR / "db.json" # 


def recv_line(sock: socket.socket) -> str:
    """Legge una riga terminata da '\n' come richiesto dal protocollo DC [cite: 251]"""
    data = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            return ""  
        if chunk == b"\n":
            break
        data.extend(chunk)
    return data.decode("utf-8", errors="replace").strip()

def mean(values):
    return sum(values) / len(values) if values else None

def main():
    # Caricamento parametri 
    try:
        with open(PARAMETRI_FILE, "r", encoding="utf-8") as file:
            parametri = json.load(file)
    except FileNotFoundError:
        print(f"Errore: File {PARAMETRI_FILE} non trovato.")
        return

    TEMPO_RILEVAZIONE = parametri["TEMPO_RILEVAZIONE"]
    N_DECIMALI = parametri["N_DECIMALI"]
    IDENTITA_GIOT = parametri["IDENTITA_GIOT"]
    TEMPO_INVIO = parametri["TEMPO_INVIO"]
    IP_SERVER = parametri["IP_SERVER"]
    PORTA_SERVER = int(parametri["PORTA_SERVER"])

    # Creazione cartella database 
    IOTP_DIR.mkdir(parents=True, exist_ok=True)

    buffer_dc = {}
    invionumero = 0
    ultimo_invio = time.time()

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
                    # Invio parametri iniziali al DC [cite: 251]
                    parametri_init = {
                        "TEMPO_RILEVAZIONE": TEMPO_RILEVAZIONE,
                        "N_DECIMALI": N_DECIMALI
                    }
                    conn.sendall((json.dumps(parametri_init) + "\n").encode("utf-8"))

                    while True:
                        line = recv_line(conn)
                        if not line:
                            break 

                        try:
                            dato_dc = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        # Debug: visualizza dati ricevuti [cite: 280]
                        print("Ricevuto da DC:")
                        print(json.dumps(dato_dc, indent=4, ensure_ascii=False))

                        identita_dc = dato_dc.get("identita")
                        camera = dato_dc.get("camera") # Allineato a dc.py
                        ponte = dato_dc.get("ponte")
                        osservazione = dato_dc.get("osservazione", {})
                        
                        t = osservazione.get("temperatura")
                        u = osservazione.get("umidita")

                        if identita_dc not in buffer_dc:
                            buffer_dc[identita_dc] = {
                                "camera": camera,
                                "ponte": ponte,
                                "temperatura": [],
                                "umidita": []
                            }

                        if isinstance(t, (int, float)):
                            buffer_dc[identita_dc]["temperatura"].append(t)
                        if isinstance(u, (int, float)):
                            buffer_dc[identita_dc]["umidita"].append(u)

                        # Verifica tempo invio [cite: 253]
                        now = time.time()
                        if now - ultimo_invio >= TEMPO_INVIO:
                            invionumero += 1
                            ultimo_invio = now

                            for dc_id, b in buffer_dc.items():
                                mt = mean(b["temperatura"])
                                mu = mean(b["umidita"])

                                if mt is None or mu is None:
                                    continue

                                # Struttura IOTdata del DA [cite: 258, 285]
                                dato_iotp = {
                                    "camera": b["camera"],
                                    "ponte": b["ponte"],
                                    "temperaturam": round(mt, N_DECIMALI),
                                    "umiditam": round(mu, N_DECIMALI),
                                    "dataeora": int(time.time()),
                                    "invionumero": invionumero,
                                    "identita": IDENTITA_GIOT
                                }

                                # Criptazione obbligatoria (anche se non effettiva) [cite: 278]
                                payload_criptato = cripto.criptazione(json.dumps(dato_iotp))

                                # Debug: visualizza dati in uscita [cite: 280]
                                print(f"Dato inviato alla piattaforma (criptato): {payload_criptato}")

                                # Salvataggio su file db.json 
                                with open(IOTP_DB_FILE, "a", encoding="utf-8") as out:
                                    out.write(json.dumps(dato_iotp) + "\n")

                                b["temperatura"].clear()
                                b["umidita"].clear()

        except KeyboardInterrupt:
            # Visualizzazione conteggio finale 
            print(f"\nTerminazione. Rilevazioni inviate alla IOTPlatform: {invionumero}")
            sys.exit(0)

if __name__ == "__main__":
    main()