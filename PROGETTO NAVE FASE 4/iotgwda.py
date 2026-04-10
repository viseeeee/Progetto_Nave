import json
import socket
import time
import paho.mqtt.client as mqtt
from pathlib import Path
import cripto
import threading # <-- 1. Importiamo la libreria per il multithreading

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "configurazione"
PARAMETRI_FILE = CONFIG_DIR / "parametri.json"

def recv_line(sock):
    data = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            return ""
        if chunk == b"\n":
            break
        data.extend(chunk)
    return data.decode("utf-8", errors="replace").strip()

# <-- 2. Creiamo una funzione che gestisce UN SINGOLO client
def gestisci_client(conn, addr, parametri, client_mqtt):
    print(f"\n[+] Nuovo sensore connesso da: {addr}")
    
    TEMPO_RILEVAZIONE = parametri["TEMPO_RILEVAZIONE"]
    N_DECIMALI = parametri["N_DECIMALI"]
    IDENTITA_GIOT = parametri["IDENTITA_GIOT"]
    TOPIC = parametri["TOPIC"]

    with conn:
        # Invio parametri iniziali al sensore
        parametri_init = {
            "TEMPO_RILEVAZIONE": TEMPO_RILEVAZIONE,
            "N_DECIMALI": N_DECIMALI
        }
        try:
            conn.sendall((json.dumps(parametri_init) + "\n").encode("utf-8"))
        except:
            print(f" Errore nell'invio dei parametri a {addr}")
            return
        
        # Ciclo di ascolto infinito (solo per questo specifico sensore)
        while True:
            try:
                line = recv_line(conn)
                if not line:
                    break # Se la riga è vuota, il sensore si è disconnesso
                
                dato_dc = json.loads(line)
                print(f"[{addr[1]}] DatoIoT ricevuto:", json.dumps(dato_dc))
                
                # Prepara DatoIoT per MQTT
                dato_iotp = {
                    "cabina": dato_dc["camera"],
                    "ponte": dato_dc["ponte"],
                    "temperaturam": round(dato_dc["osservazione"]["temperatura"], N_DECIMALI),
                    "umiditam": round(dato_dc["osservazione"]["umidita"], N_DECIMALI),
                    "dataeora": dato_dc["osservazione"]["dataeora"],
                    "invionumero": dato_dc["osservazione"]["rilevazione"],
                    "identita": IDENTITA_GIOT
                }
                
                # CRIPTA
                payload_criptato = cripto.criptazione(json.dumps(dato_iotp))
                print(f"[{addr[1]}] Gateway in invio (MQTT):", payload_criptato)
                
                # PUBBLICA su MQTT
                client_mqtt.publish(TOPIC, payload_criptato)
                
            except Exception as e:
                print(f"[-] Errore di comunicazione con {addr}: {e}")
                break
                
    print(f"[-] Sensore {addr} disconnesso.")

def main():
    # Legge parametri.json
    with open(PARAMETRI_FILE, "r", encoding="utf-8") as f:
        parametri = json.load(f)

    IP_SERVER = parametri["IP_SERVER"]
    PORTA_SERVER = int(parametri["PORTA_SERVER"])
    BROKER = parametri["BROKER"]
    PORTA_BROKER = int(parametri["PORTA_BROKER"])

    # Connessione MQTT publisher
    client = mqtt.Client()
    client.connect(BROKER, PORTA_BROKER, 60)
    client.loop_start()

    # Socket server TCP
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((IP_SERVER, PORTA_SERVER))
        server.listen()
        
        # TRUCCO PER WINDOWS: Imposta un timeout di 1 secondo
        server.settimeout(1.0) 
        
        print(f"Gateway IoT in attesa di dati su {IP_SERVER}:{PORTA_SERVER}...")
        
        try:
            while True:
                try:
                    # Il server aspetta per 1 secondo...
                    conn, addr = server.accept()
                    
                    # Se qualcuno si connette, lancia il thread
                    thread_client = threading.Thread(target=gestisci_client, args=(conn, addr, parametri, client))
                    thread_client.daemon = True 
                    thread_client.start()
                    
                except socket.timeout:
                    # Se passa 1 secondo e nessuno si connette, il codice passa di qua
                    # Questo permette a Python di "sentire" se hai premuto Ctrl+C!
                    pass 
                    
        except KeyboardInterrupt:
            print("\n Spegnimento manuale del Gateway in corso.")

if __name__ == "__main__":
    main()