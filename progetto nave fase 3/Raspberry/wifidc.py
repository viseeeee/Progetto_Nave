import json
import time
import network
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WIFI_FILE = os.path.join(BASE_DIR, "wifipico.json")


def connetti_wifi(wifi_file=WIFI_FILE, timeout_s=20, sleep_s=0.5):
    """
    Legge wifipico.json:
      {"ssid": "...", "pw": "..."}
    e connette il Pico W alla Wi-Fi.
    """
    with open(wifi_file, "r") as f:
        cfg = json.load(f)

    ssid = cfg["ssid"]
    pw = cfg["pw"]

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(ssid, pw)

        t0 = time.time()
        while not wlan.isconnected():
            if time.time() - t0 >= timeout_s:
                raise RuntimeError("Timeout connessione Wi-Fi")
            time.sleep(sleep_s)

    return wlan


def info(wlan):
    return {
        "connesso": wlan.isconnected(),
        "ifconfig": wlan.ifconfig() if wlan.isconnected() else None
    }


def main():
    wlan = connetti_wifi()
    print(info(wlan))


if __name__ == "__main__":
    main()
