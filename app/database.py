import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    """Класс для работы с базой данных PostgreSQL"""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = os.getenv('DB_PORT', '5432')
        self.user = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', '')
        self.database = os.getenv('DB_NAME', 'movie_reviews')
    
    def get_connection(self):
        """
        Создает и возвращает подключение к PostgreSQL
        """
        try:
            connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                connect_timeout=10
            )
            return connection
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            raise

# Глобальный экземпляр базы данных
db = Database()

def get_db_connection():
    """
    Функция для получения подключения к БД
    """
    return db.get_connection()

def init_db():
    """
    Инициализация базы данных - проверка подключения и таблиц
    """
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Проверяем существование таблиц
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            print("✅ Таблицы в базе данных:")
            for table in tables:
                print(f"   - {table[0]}")
            
            # Проверяем количество записей (используем индексы вместо ключей)
            cursor.execute("SELECT COUNT(*) as count FROM movies")
            movies_count = cursor.fetchone()[0]  # Используем индекс [0] вместо ['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM reviews")
            reviews_count = cursor.fetchone()[0]  # Используем индекс [0] вместо ['count']
            
            print(f"📊 Статистика: {movies_count} фильмов, {reviews_count} отзывов")
            
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        raise
    finally:
        if connection:
            connection.close()

def test_connection():
    """
    Тестирование подключения к базе данных
    """
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Подключение к PostgreSQL успешно!")
            print(f"📋 Версия: {version[0]}")
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False
    finally:
        if connection:
            connection.close()