# ==========================================================
# 📲 TELEGRAM ALERTS – PECHEURCONNECT 🇸🇳 (PRODUCTION)
# ==========================================================

import os
import requests
from datetime import datetime


def send_telegram_message(message: str):
    """
    Envoie un message Telegram sans bloquer le script principal
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("⚠️ Telegram non configuré (variables manquantes)")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("📲 Telegram envoyé avec succès")
        else:
            print("⚠️ Erreur Telegram:", r.text)
    except Exception as e:
        print("❌ Exception Telegram:", e)


# ==========================================================
# 📡 MESSAGE AUTOMATIQUE APRÈS GÉNÉRATION DE data.json
# ==========================================================

try:
    summary_lines = []
    danger_detected = False

    # ⚠️ data = liste Python déjà utilisée pour écrire data.json
    for zone in data:
        zone_name = zone.get("zone", "Zone inconnue")
        houle = float(zone.get("vhm0", 0))
        score = int(zone.get("score_peche", 0))
        temp = zone.get("temp", "?")
        vent = zone.get("wind_speed", "?")

        # Logique alerte
        if houle >= 2.2:
            emoji = "🔴"
            danger_detected = True
        elif score >= 60:
            emoji = "🟢"
        else:
            emoji = "🟠"

        summary_lines.append(
            f"{emoji} *{zone_name}*\n"
            f"🎯 Score: {score}\n"
            f"🌊 Houle: {houle} m\n"
            f"🌡️ Temp: {temp} °C\n"
            f"🌬️ Vent: {vent} km/h\n"
        )

    header = (
        "🚨 *ALERTE MER DANGEREUSE – PECHEURCONNECT* 🚨\n\n"
        if danger_detected
        else "📡 *PêcheurConnect – Données Copernicus à jour*\n\n"
    )

    footer = (
        "\n🕒 "
        + datetime.utcnow().strftime("%d-%m-%Y %H:%M UTC")
        + "\n🌊 Données satellites Copernicus Marine"
    )

    telegram_message = header + "\n".join(summary_lines) + footer

    send_telegram_message(telegram_message)

except Exception as e:
    print("⚠️ Envoi Telegram ignoré :", e)
