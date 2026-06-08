import subprocess
import time

# --- KONFIGURATION ---
PORT = "/dev/ttyACM0"    # Standard-Port für ESP32 unter Ubuntu 
REGION = "EU_868"
CHANNEL_NAME = "TAK-Passau"
PSK = "exIn1wKKMSNayVOCzzqbMGK9INh6OqUZ+JMHt/SklYk=" 

def run_command(cmd):
    print(f"Führe aus: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("Erfolgreich!")
    else:
        print(f"Fehler:\n{result.stderr}")
    time.sleep(3) # Kurze Pause für den Flash-Speicher

print("Starte Meshtastic Provisioning (Ubuntu)...\n")

commands = [
    f"python3 -m meshtastic --port {PORT} --set lora.region {REGION}",
    f"python3 -m meshtastic --port {PORT} --ch-index 0 --ch-set name {CHANNEL_NAME} --ch-set psk {PSK}",
    f"python3 -m meshtastic --port {PORT} --set position.smart_broadcast_sec 120",
    f"python3 -m meshtastic --port {PORT} --set display.screen_on_secs 300"
]

for command in commands:
    run_command(command)

print("\nSetup abgeschlossen! Gerät kann jetzt an den Docker-Dienst übergeben werden.")