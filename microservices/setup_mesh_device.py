import subprocess
import time

# --- KONFIGURATION ---
PORT = "/dev/ttyACM0"
REGION = "EU_868"
CHANNEL_NAME = "TAK-Passau"
PSK = "exIn1wKKMSNayVOCzzqbMGK9INh6OqUZ+JMHt/SklYk="

def run_command(cmd, wait_time=3):
    print(f"⏳ Führe aus: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Erfolgreich!")
    else:
        print(f"❌ Fehler:")
        # Verbesserte Fehlerausgabe: Liest sowohl stderr als auch stdout
        if result.stderr.strip():
            print(f"   STDERR: {result.stderr.strip()}")
        if result.stdout.strip():
            print(f"   STDOUT: {result.stdout.strip()}")
            
    print(f"   Warte {wait_time} Sekunden...")
    time.sleep(wait_time)

print("🚀 Starte Meshtastic Provisioning (Ubuntu)...\n")

# Die Befehle als Liste von Tuples: (Befehl, Wartezeit_danach)
commands = [
    # 1. Region setzen -> löst oft Reboot aus, daher 10 Sekunden warten!
    (f"python3 -m meshtastic --port {PORT} --set lora.region {REGION}", 10),
    
    # 2. Kanal & PSK setzen -> Hier sind jetzt '{CHANNEL_NAME}' und '{PSK}' mit Quotes geschützt!
    (f"python3 -m meshtastic --port {PORT} --ch-index 0 --ch-set name '{CHANNEL_NAME}' --ch-set psk '{PSK}'", 5),
    
    # 3. Position Broadcast
    (f"python3 -m meshtastic --port {PORT} --set position.smart_broadcast_sec 120", 3),
    
    # 4. Display Timeout
    (f"python3 -m meshtastic --port {PORT} --set display.screen_on_secs 300", 3)
]

for cmd, wait_time in commands:
    run_command(cmd, wait_time)

print("\n🎉 Setup abgeschlossen! Gerät kann jetzt an den Docker-Dienst übergeben werden.")