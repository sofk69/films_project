import uvicorn
import threading
import subprocess
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def run_bot():
    try:
        print("🤖 Запускаем Telegram бота...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        bot_path = os.path.join(current_dir, "bot", "bot.py")
        
        if os.path.exists(bot_path):
            print(f"✅ Найден файл бота: {bot_path}")
            subprocess.run([sys.executable, bot_path], check=True)
        else:
            print("❌ Файл bot.py не найден")
            
    except Exception as e:
        print(f"❌ Ошибка в боте: {e}")

def run_website():
    try:
        print("🌐 Запускаем веб-сайт...")
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0", 
            port=8000,
            reload=False
        )
    except Exception as e:
        print(f"❌ Ошибка запуска сайта: {e}")

if __name__ == "__main__":
    print("🚀 Запускаем приложение...")
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("⚠️ TELEGRAM_BOT_TOKEN не найден. Запускаем только веб-сайт...")
        run_website()
    else:
        print("✅ TELEGRAM_BOT_TOKEN найден")
        
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        
        run_website()