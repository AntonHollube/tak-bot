import subprocess
import time

# --- KONFIGURATION ---
PORT = "/dev/ttyACM0"
REGION = "EU_868"
CHANNEL_NAME = "TAK-Passau"
# WICHTIG: Das Präfix 'base64:' MUSS direkt vor dem eigentlichen Schlüssel stehen!
PSK = "base64:exIn1wKKMSNayVOCzzqbMGK9INh6OqUZ+JMHt/SklYk="

def run_command(cmd, wait_time=3):
    print(f"⏳ Führe aus: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Erfolgreich!")
    else:
        print(f"❌ Fehler:")
        if result.stderr.strip():
            print(f"   STDERR: {result.stderr.strip()}")
        if result.stdout.strip():
            print(f"   STDOUT: {result.stdout.strip()}")
            
    print(f"   Warte {wait_time} Sekunden...\n")
    time.sleep(wait_time)

print("🚀 Starte Meshtastic Provisioning (Ubuntu)...\n")

commands = [
    # 1. Region
    (f"python3 -m meshtastic --port {PORT} --set lora.region {REGION}", 10),
    
    # 2. Kanal & PSK (mit dem korrekten base64: Präfix in der Variable)
    (f"python3 -m meshtastic --port {PORT} --ch-index 0 --ch-set name '{CHANNEL_NAME}' --ch-set psk '{PSK}'", 5),
    
    # 3. Position Broadcast
    (f"python3 -m meshtastic --port {PORT} --set position.smart_broadcast_sec 120", 3),
    
    # 4. Display Timeout
    (f"python3 -m meshtastic --port {PORT} --set display.screen_on_secs 300", 3)
]

for cmd, wait_time in commands:
    run_command(cmd, wait_time)

print("🎉 Setup abgeschlossen! Gerät kann jetzt an den Docker-Dienst übergeben werden.")