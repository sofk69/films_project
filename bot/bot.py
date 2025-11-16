import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import pg8000
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

class MovieBot:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'movie_reviews')
        }
    
    def get_db_connection(self):
        try:
            connection = pg8000.connect(**self.db_config)
            return connection
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None

    def get_movie_data(self, cursor, sql, params=None):
        try:
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()
            if not rows:
                return []
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return []
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        conn = self.get_db_connection()
        db_status = "✅ База данных подключена" if conn else "❌ База данных недоступна"
        if conn:
            conn.close()
        
        welcome_text = f"""
🎬 Привет, {user.first_name}!

Я бот для поиска фильмов и отзывов.
{db_status}

Доступные команды:
/start - показать это сообщение
/search <запрос> - поиск фильмов по названию
/top - топ фильмов
/help - помощь

Напиши /search чтобы начать поиск!
        """
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
📖 Помощь по командам:

/search <название> - поиск фильмов по названию
Пример: /search начало

/top - показать топ-5 фильмов
/help - эта справка

Просто напиши название фильма для быстрого поиска!
        """
        await update.message.reply_text(help_text)
    
    async def search_movies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("🔍 Укажите название фильма для поиска:\n/search <название>")
            return
        
        search_query = " ".join(context.args)
        connection = self.get_db_connection()
        
        if not connection:
            await update.message.reply_text("❌ Ошибка подключения к базе данных")
            return
        
        try:
            cursor = connection.cursor()
            
            sql_search = """
            SELECT m.id, m.title, m.director, m.release_year, m.genre,
                   COALESCE(AVG(r.rating), 0) as avg_rating,
                   COUNT(r.id) as review_count
            FROM movies m
            LEFT JOIN reviews r ON m.id = r.movie_id
            WHERE m.title ILIKE %s
            GROUP BY m.id, m.title, m.director, m.release_year, m.genre
            ORDER BY avg_rating DESC
            LIMIT 10
            """
            search_term = f"%{search_query}%"
            cursor.execute(sql_search, (search_term,))
            movies = self.get_movie_data(cursor, sql_search, (search_term,))
            
            if not movies:
                await update.message.reply_text(f"😔 Фильмы по запросу '{search_query}' не найдены")
                return
            
            if len(movies) == 1:
                await self.show_movie_details(update, context, movies[0]['id'])
                return
            
            response = f"🎭 Найдено фильмов: {len(movies)}\n\n"
            
            for movie in movies:
                rating = round(float(movie['avg_rating'] or 0), 1)
                response += f"🎬 <b>{movie['title']}</b>\n"
                response += f"📀 Режиссер: {movie['director']}\n"
                response += f"⭐ Рейтинг: {rating}/10\n"
                response += f"💬 Отзывов: {movie['review_count']}\n"
                
                if movie['release_year']:
                    response += f"📅 Год: {movie['release_year']}\n"
                
                response += "\n" + "─" * 30 + "\n\n"
            
            response += "💡 <i>Напишите точное название фильма для просмотра отзывов</i>"
            
            await update.message.reply_text(response, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            await update.message.reply_text("❌ Произошла ошибка при поиске")
        finally:
            connection.close()

    async def show_movie_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, movie_id=None):
        if movie_id is None:
            text = update.message.text.strip()
            connection = self.get_db_connection()
            if not connection:
                await update.message.reply_text("❌ Ошибка подключения к базе данных")
                return
            
            try:
                cursor = connection.cursor()
                sql = "SELECT id FROM movies WHERE title ILIKE %s"
                cursor.execute(sql, (text,))
                result = cursor.fetchone()
                if result:
                    movie_id = result[0]
                else:
                    await update.message.reply_text(f"😔 Фильм '{text}' не найден. Используйте /search для поиска.")
                    return
            except Exception as e:
                logger.error(f"Movie ID search error: {e}")
                await update.message.reply_text("❌ Произошла ошибка при поиске фильма")
                return
            finally:
                connection.close()
        
        connection = self.get_db_connection()
        
        if not connection:
            await update.message.reply_text("❌ Ошибка подключения к базе данных")
            return
        
        try:
            cursor = connection.cursor()
            
            sql_movie = """
            SELECT m.id, m.title, m.director, m.release_year, m.genre, m.description,
                   COALESCE(AVG(r.rating), 0) as avg_rating,
                   COUNT(r.id) as review_count
            FROM movies m
            LEFT JOIN reviews r ON m.id = r.movie_id
            WHERE m.id = %s
            GROUP BY m.id, m.title, m.director, m.release_year, m.genre, m.description
            """
            cursor.execute(sql_movie, (movie_id,))
            movies = self.get_movie_data(cursor, sql_movie, (movie_id,))
            
            if not movies:
                await update.message.reply_text("❌ Фильм не найден")
                return
            
            movie = movies[0]
            
            sql_reviews = """
            SELECT rating, review_text, created_at, user_name
            FROM reviews 
            WHERE movie_id = %s 
            ORDER BY created_at DESC 
            LIMIT 3
            """
            cursor.execute(sql_reviews, (movie_id,))
            reviews = self.get_movie_data(cursor, sql_reviews, (movie_id,))
            
            response = f"🎬 <b>{movie['title']}</b>\n"
            response += f"📀 Режиссер: {movie['director']}\n"
            response += f"⭐ Средний рейтинг: {round(float(movie['avg_rating']), 1)}/10\n"
            response += f"📊 Всего отзывов: {movie['review_count']}\n"
            
            if movie['release_year']:
                response += f"📅 Год выпуска: {movie['release_year']}\n"
            
            if movie['genre']:
                response += f"🎭 Жанр: {movie['genre']}\n"
            
            response += "\n🎞️ Последние отзывы:\n"
            
            if reviews:
                for i, review in enumerate(reviews, 1):
                    response += f"\n{i}. ⭐ {review['rating']}/10"
                    if review.get('user_name'):
                        response += f" от {review['user_name']}"
                    response += "\n"
                    if review['review_text']:
                        review_text = review['review_text']
                        if len(review_text) > 100:
                            review_text = review_text[:100] + "..."
                        response += f"   {review_text}\n"
            else:
                response += "\n😔 Отзывов пока нет\n"
            
            await update.message.reply_text(response, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Movie details error: {e}")
            await update.message.reply_text(f"❌ Произошла ошибка при получении информации о фильме: {str(e)}")
        finally:
            connection.close()

    async def top_movies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        connection = self.get_db_connection()
        
        if not connection:
            await update.message.reply_text("❌ Ошибка подключения к базе данных")
            return
        
        try:
            cursor = connection.cursor()
            sql = """
            SELECT m.id, m.title, m.director, m.release_year, m.genre,
                   COALESCE(AVG(r.rating), 0) as avg_rating,
                   COUNT(r.id) as review_count
            FROM movies m
            LEFT JOIN reviews r ON m.id = r.movie_id
            GROUP BY m.id, m.title, m.director, m.release_year, m.genre
            HAVING COUNT(r.id) > 0
            ORDER BY avg_rating DESC
            LIMIT 5
            """
            cursor.execute(sql)
            movies = self.get_movie_data(cursor, sql)
            
            if not movies:
                await update.message.reply_text("😔 В базе пока нет фильмов с отзывами")
                return
            
            response = "🏆 ТОП-5 фильмов по рейтингу:\n\n"
            
            for i, movie in enumerate(movies, 1):
                rating = round(float(movie['avg_rating'] or 0), 1)
                response += f"{i}. <b>{movie['title']}</b>\n"
                response += f"   ⭐ {rating}/10 ({movie['review_count']} отзывов)\n"
                response += f"   📀 {movie['director']}\n\n"
            
            await update.message.reply_text(response, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Top movies error: {e}")
            await update.message.reply_text("❌ Произошла ошибка")
        finally:
            connection.close()
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        
        if text.startswith('/'):
            return
        
        await update.message.reply_text(f"🔍 Ищу фильм: '{text}'...")
        await self.show_movie_details(update, context)

def main():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не установлен")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    bot = MovieBot()
    
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("search", bot.search_movies))
    application.add_handler(CommandHandler("top", bot.top_movies))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text))
    
    print("🤖 Бот запускается...")
    application.run_polling()

if __name__ == '__main__':
    main()