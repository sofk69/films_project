from fastapi import APIRouter, HTTPException, Query
from typing import List
import app.database as database
import app.models as models

router = APIRouter()

@router.get("/users", response_model=List[models.User])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Получить список пользователей
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            SELECT * FROM users 
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (limit, skip))
            users = cursor.fetchall()
            
        return users
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения пользователей: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.post("/users", response_model=dict)
async def create_user(user: models.UserCreate):
    """
    Создать нового пользователя
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", 
                         (user.username, user.email))
            existing_user = cursor.fetchone()
            if existing_user:
                raise HTTPException(status_code=400, detail="Пользователь с таким username или email уже существует")
            
            sql = """
            INSERT INTO users (username, email)
            VALUES (%s, %s)
            RETURNING id
            """
            cursor.execute(sql, (user.username, user.email))
            user_id = cursor.fetchone()['id']
            connection.commit()
            
        return {"message": "Пользователь успешно создан", "user_id": user_id}
    
    except HTTPException:
        raise
    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания пользователя: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.get("/users/{user_id}", response_model=models.User)
async def get_user(user_id: int):
    """
    Получить пользователя по ID
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(status_code=404, detail="Пользователь не найден")
            
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения пользователя: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.get("/stats", response_model=models.StatsResponse)
async def get_stats():
    """
    Получить статистику по фильмам и отзывам
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total_movies FROM movies")
            total_movies = cursor.fetchone()['total_movies']
            
            cursor.execute("SELECT COUNT(*) as total_reviews FROM reviews")
            total_reviews = cursor.fetchone()['total_reviews']
            
            cursor.execute("SELECT COUNT(*) as total_users FROM users")
            total_users = cursor.fetchone()['total_users']
            
            cursor.execute("SELECT AVG(rating) as avg_rating FROM reviews")
            avg_rating = cursor.fetchone()['avg_rating']
            
            cursor.execute("""
                SELECT genre, COUNT(*) as count 
                FROM movies 
                WHERE genre IS NOT NULL 
                GROUP BY genre 
                ORDER BY count DESC 
                LIMIT 1
            """)
            top_genre_result = cursor.fetchone()
            top_genre = top_genre_result['genre'] if top_genre_result else None
            
            cursor.execute("""
                SELECT m.title, COUNT(r.id) as review_count
                FROM movies m
                LEFT JOIN reviews r ON m.id = r.movie_id
                GROUP BY m.id, m.title
                ORDER BY review_count DESC
                LIMIT 1
            """)
            most_reviewed = cursor.fetchone()
            most_reviewed_movie = most_reviewed['title'] if most_reviewed else None
            
        return models.StatsResponse(
            total_movies=total_movies,
            total_reviews=total_reviews,
            average_rating=round(float(avg_rating or 0), 2),
            top_genre=top_genre,
            most_reviewed_movie=most_reviewed_movie,
            total_users=total_users
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")
    
    finally:
        if connection:
            connection.close()