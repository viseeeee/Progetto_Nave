import json
import socket
import time
import sys
from pathlib import Path
# Importa il modulo di criptazione
import cripto 

# Stringa contenente il percorso assoluto della cartella DA
BASE_DIR = Path(__file__).resolve().parent
# Costruisce una stringa con il percorso di parametri.conf
PARAMETRI_FILE = BASE_DIR / "parametri.json"
# Percorso in cui si trova la cartella DA
PROJECT_DIR = BASE_DIR.parent
# Costruisce una stringa con il percorso della cartella IOTP
IOTP_DIR = PROJECT_DIR / "IOTP"
# Costruisce una stringa con il percorso di iotdata.dbt
IOTP_DB_FILE = IOTP_DIR / "iotdata.dbt"


def recv_line(sock: socket.socket) -> str:
    """Legge da un socket una riga di testo terminata da '\n' (ricevendo 1 byte alla volta).
    Accumula i byte in un buffer; se la connessione viene chiusa (recv ritorna b''), restituisce una stringa vuota.
    Converte i dati ricevuti in una stringa rimuovendo spazi e \n.
    """
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
    """ Metodo che fa la media dei numeri
    """
    return sum(values) / len(values) if values else None


def main():
    #Legge il file parametri.conf e vengono salvati in configurazione.
    with open(PARAMETRI_FILE, "r", encoding="utf-8") as file:
        parametri = json.load(file)

    TEMPO_RILEVAZIONE = parametri["TEMPO_RILEVAZIONE"]
    N_DECIMALI = parametri["N_DECIMALI"]
    IDENTITA_GIOT = parametri["IDENTITA_GIOT"]
    TEMPO_INVIO = parametri["TEMPO_INVIO"]
    IP_SERVER = parametri["IP_SERVER"]
    PORTA_SERVER = int(parametri["PORTA_SERVER"])

    #Crea la cartella IOTP
    IOTP_DIR.mkdir(parents=True, exist_ok=True)

    buffer_dc = {}
    
    invionumero = 0
    ultimo_invio = time.time()

    #Avvio della socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #Associa la socket
        server.bind((IP_SERVER, PORTA_SERVER))
        #Il server rimane in ascolto per le prossime 5 connessioni
        server.listen(5)

        print(f"DA in ascolto su {IP_SERVER}:{PORTA_SERVER}")
        print("CTRL+C per terminare.")

        try:
            while True:
                #Accetta la connessione con il client
                conn,addr= server.accept()
                with conn:
                    parametri_init = {
                        "TEMPO_RILEVAZIONE": TEMPO_RILEVAZIONE,
                        "N_DECIMALI": N_DECIMALI
                    }
                    
                    #Invia i dati a DC 
                    conn.sendall((json.dumps(parametri_init) + "\n").encode("utf-8"))
                   
                    while True:
                        line = recv_line(conn)# Riceve i dati dal client
                        if line == "":
                            break 

                        try:
                            dato_dc = json.loads(line)# Converte i dati ricevuti in una stringa
                        except json.JSONDecodeError:
                            print(f"Ricevuto non-JSON: {line!r}")
                            continue

                        print("Ricevuto da DC:")
                        print(json.dumps(dato_dc, indent=4, ensure_ascii=False))
                        identita_dc = dato_dc.get("identita")
                        camera = dato_dc.get("camera")
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

                        # Accumulo i dati per le medie
                        if isinstance(t, (int, float)):
                            buffer_dc[identita_dc]["temperatura"].append(t)
                        if isinstance(u, (int, float)):
                            buffer_dc[identita_dc]["umidita"].append(u)

                        # Ogni TEMPO_INVIO minuti genero invio verso IOTP
                        now = time.time()
                        if now - ultimo_invio >= TEMPO_INVIO:
                            invionumero += 1
                            ultimo_invio = now
                            # Crea la media per la temperatura e per l'umidità
                            for dc_id, b in buffer_dc.items():
                                mt = mean(b["temperatura"])
                                mu = mean(b["umidita"])

                                if mt is None or mu is None:
                                    continue

                                dato_iotp = {
                                    "invionumero": invionumero,
                                    "camera": b["camera"],
                                    "ponte": b["ponte"],
                                    "temperatura": round(mt, N_DECIMALI),
                                    "umidita": round(mu, N_DECIMALI),
                                    "dateora": int(time.time()),
                                    "identita": IDENTITA_GIOT,
                                    "dc": dc_id
                                }
                                # Criptazione
                                dato_iot_dc_json = json.dumps(dato_iotp)
                                dato_iot_dc_json_criptato = cripto.criptazione(dato_iot_dc_json)
                                # Stampo dato criptato 
                                print("Da inviare a IOTPlatform (criptato):")
                                print(dato_iot_dc_json_criptato)
                                print("SALVO ORA su:", IOTP_DB_FILE)
                                print("dato_iot_dc_json:", dato_iot_dc_json)
                                # Salvo il dato non criptato su file iotdata.dbt
                                with open(IOTP_DB_FILE, "a", encoding="utf-8") as out:
                                    out.write(dato_iot_dc_json + "\n")
                                # Azzero buffer dopo invio 
                                b["temperatura"].clear()
                                b["umidita"].clear()

        except KeyboardInterrupt:
            print("\nTerminazione DA da tastiera.")
            print(f"Invii effettuati verso IoTPlatform: {invionumero}")
            sys.exit(0)


if __name__ == "__main__":
    main()
    
