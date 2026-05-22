import os
import smtplib
import json
import urllib.request
from email.mime.text import MIMEText

def cargar_env():
    """Lee las credenciales directamente del archivo .env"""
    try:
        with open('.env') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    except FileNotFoundError:
        print("❌ Error: Archivo .env no encontrado en esta carpeta.")

cargar_env()

print("--- 📡 INICIANDO TEST DE ALERTAS DEL ARQUITECTO ---")

# ==========================================
# 1. TEST DE TELEGRAM
# ==========================================
token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

if token and chat_id:
    print(f"\n[Telegram] Probando conexión para el Chat ID: {chat_id}...")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    mensaje = {"chat_id": chat_id, "text": "🤖 Arquitecto: ¡Conexión a Telegram exitosa! El sistema está listo 24/7."}
    data = json.dumps(mensaje).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print("✅ Telegram: ¡Mensaje enviado! Revisa tu móvil.")
            else:
                print(f"❌ Telegram: Error de API ({response.status})")
    except Exception as e:
        print(f"❌ Telegram: Error de conexión - Verifica tu Token. Detalle: {e}")
else:
    print("\n⚠️ Telegram: Omitido (Faltan credenciales en el .env)")

# ==========================================
# 2. TEST DE EMAIL (SMTP)
# ==========================================
smtp_host = os.getenv("SMTP_HOST")
smtp_port = os.getenv("SMTP_PORT", "587")
user = os.getenv("SMTP_USER")
pwd = os.getenv("SMTP_PASSWORD")
to_email = os.getenv("SMTP_TO")

if smtp_host and user and pwd and to_email:
    print(f"\n[Email] Probando envío hacia: {to_email}...")
    msg = MIMEText("🤖 Arquitecto: ¡Conexión a Email exitosa! El sistema de alertas está operativo.")
    msg['Subject'] = 'Test Alerta Arquitecto'
    msg['From'] = user
    msg['To'] = to_email

    try:
        server = smtplib.SMTP(smtp_host, int(smtp_port))
        server.starttls()
        server.login(user, pwd)
        server.send_message(msg)
        server.quit()
        print("✅ Email: ¡Mensaje enviado! Revisa tu bandeja de entrada (y la carpeta de Spam).")
    except Exception as e:
        print(f"❌ Email: Error de conexión - Verifica tu contraseña de aplicación. Detalle: {e}")
else:
    print("\n⚠️ Email: Omitido (Faltan credenciales en el .env)")

print("\n--- TEST FINALIZADO ---")
