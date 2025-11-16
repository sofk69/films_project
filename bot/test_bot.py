import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import pg8000

load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    try:
        conn = pg8000.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM movies")
        count = cursor.fetchone()[0]
        conn.close()
        db_status = f"✅ PostgreSQL: {count} фильмов в базе"
    except Exception as e:
        db_status = f"❌ Ошибка: {str(e)}"
    
    await update.message.reply_text(f"🎬 Привет, {user.first_name}!\n{db_status}")

def main():
    if not BOT_TOKEN:
        print("❌ Токен не найден")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    print("🤖 Бот с pg8000 запускается...")
    application.run_polling()

if __name__ == '__main__':
    main()