import os, requests
token = os.getenv("TG_TOKEN")
chat_id = os.getenv("TG_ID")
requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
              data={"chat_id": chat_id, "text": "🔔 TEST PRIORITAIRE : GitHub communique avec ton Telegram !"})
print("Tentative d'envoi effectuée.")
