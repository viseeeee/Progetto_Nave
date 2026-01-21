import json
import time
import os
import random

# Importa il modulo misurazione per simulare temperatura e umidità.
import misurazione 

# Costruisce una stringa con il percorso di parametri.conf.
CONFIG_PATH = os.path.join("configurazione", "parametri.conf")

# Costruisce una stringa con il percorso di iodata.dbt che si trova dentro la cartella dati.
DATI_DIR = "dati"
ARCHIVIO_PATH = os.path.join(DATI_DIR, "iotdata.dbt")


def carica_parametri():
    """Legge il file parametri.conf e restituisce i parametri come dizionario.

    Gestisce le eccezioni di file non trovato e di JSON non valido.
    """
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            parametri = json.load(file)
            return parametri
    except FileNotFoundError as e:
        print(f"Errore: file di configurazione non trovato: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"Errore nel JSON di configurazione: {e}")
        raise


def prepara_dati():
    """Crea la cartella dati se non esiste."""
    os.makedirs(DATI_DIR, exist_ok=True)


def genera_cabina_ponte(n_cabine, n_ponti):
    """Genera casualmente il numero di cabina e il numero di ponte.

        I valori sono compresi tra 1 e n_cabine / n_ponti.
        """
    cabina = random.randint(1, n_cabine)
    ponte = random.randint(1, n_ponti)
    return cabina, ponte


def main():
    try:
        parametri = carica_parametri()# Legge parametri.conf e viene salvato in parametri.
        tempo_rilevazione = parametri["TEMPO_RILEVAZIONE"]
        n_decimali = parametri["N_DECIMALI"]
        n_cabine = parametri["N_CABINE"]
        n_ponti = parametri["N_PONTI"]
    except Exception:
        return

    prepara_dati()

    conteggio = 0
    somma_temp = 0.0
    somma_umid = 0.0
    seriale = 0

    try:
        while True:
            rilevazione += 1

            # Generazione dei vari dati
            cabina, ponte = genera_cabina_ponte(n_cabine, n_ponti)
            temperatura = misurazione.on_temperatura(n_decimali)
            umidita = misurazione.on_umidita(n_decimali)
            timestamp = time.time()

            # Formato in cui vengono stampati e poi salvati i dati
            dato_iot = {
                "cabina": cabina,
                "ponte": ponte,
                "rilevazione": rilevazione,
                "dataeora": timestamp,
                "temperatura": temperatura,
                "umidita": umidita,
            }

            # Stampa a video il DatoIoT
            print(json.dumps(dato_iot, indent=4))

            # Salva il DatoIoT su file in append
            try:
                with open(ARCHIVIO_PATH, "a", encoding="utf-8") as file:
                    file.write(json.dumps(dato_iot) + "\n")
            except OSError as e:
                print(f"Errore scrittura archivio: {e}")

            conteggio += 1
            somma_temp += temperatura
            somma_umid += umidita

            time.sleep(tempo_rilevazione)

    # Genera un'eccezione quando il programma viene terminato con CTRL+C
    except KeyboardInterrupt:
        print("\nInterruzione rilevazioni.")

        # Calcola le statistiche finali
        if conteggio > 0:
            media_temp = round(somma_temp / conteggio, n_decimali)
            media_umid = round(somma_umid / conteggio, n_decimali)
        else:
            media_temp = 0
            media_umid = 0

        # Stampa le statistiche finali
        print(f"Numero rilevazioni: {conteggio}")
        print(f"Temperatura media: {media_temp}")
        print(f"Umidità media: {media_umid}")

    except Exception as e:
        print(f"Errore imprevisto: {e}")

    finally:
        print("Fine esecuzione simulaiotdata.py.")


if __name__ == "__main__":
    main()
