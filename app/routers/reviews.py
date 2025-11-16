from fastapi import APIRouter, HTTPException, Request, Form, Query
from fastapi.responses import RedirectResponse
from typing import List, Optional
import app.database as database
import app.models as models

router = APIRouter()

@router.post("/movies/{movie_id}/reviews", response_model=dict)
async def add_review(movie_id: int, review: models.ReviewCreate):
    """
    Добавить отзыв к фильму (API)
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, title FROM movies WHERE id = %s", (movie_id,))
            movie = cursor.fetchone()
            if not movie:
                raise HTTPException(status_code=404, detail="Фильм не найден")
            
            sql = """
            INSERT INTO reviews (movie_id, user_name, rating, review_text) 
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """
            cursor.execute(sql, (
                movie_id,
                review.user_name,
                review.rating,
                review.review_text
            ))
            review_id = cursor.fetchone()['id']
            connection.commit()
            
        return {
            "message": "Отзыв успешно добавлен",
            "review_id": review_id,
            "movie_title": movie['title']
        }
    
    except HTTPException:
        raise
    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка добавления отзыва: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.post("/movies/{movie_id}/reviews/web")
async def add_review_web(
    request: Request,
    movie_id: int,
    user_name: str = Form(..., min_length=1, max_length=100),
    rating: int = Form(..., ge=1, le=10),
    review_text: str = Form("")
):
    """
    Добавить отзыв через веб-форму
    """
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM movies WHERE id = %s", (movie_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Фильм не найден")
            
            sql = """
            INSERT INTO reviews (movie_id, user_name, rating, review_text) 
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (movie_id, user_name.strip(), rating, review_text.strip() or None))
            connection.commit()
            
        return RedirectResponse(url=f"/movies/{movie_id}", status_code=303)
    
    except HTTPException:
        raise
    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка добавления отзыва: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.get("/movies/{movie_id}/reviews", response_model=List[models.Review])
async def get_movie_reviews(
    movie_id: int,
    skip: int = Query(0, ge=0, description="Пропустить записей"),
    limit: int = Query(50, ge=1, le=100, description="Лимит записей"),
    sort: str = Query("newest", description="Сортировка: newest, oldest, highest, lowest")
):
    """
    Получить отзывы для фильма с пагинацией и сортировкой
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM movies WHERE id = %s", (movie_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Фильм не найден")
            
            order_by = {
                "newest": "created_at DESC",
                "oldest": "created_at ASC",
                "highest": "rating DESC, created_at DESC",
                "lowest": "rating ASC, created_at DESC"
            }.get(sort, "created_at DESC")
            
            sql = f"""
            SELECT * FROM reviews 
            WHERE movie_id = %s 
            ORDER BY {order_by}
            LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (movie_id, limit, skip))
            reviews = cursor.fetchall()
            
        return reviews
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения отзывов: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.get("/reviews/latest", response_model=List[models.Review])
async def get_latest_reviews(limit: int = Query(10, ge=1, le=50)):
    """
    Получить последние отзывы
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            SELECT r.*, m.title as movie_title
            FROM reviews r
            JOIN movies m ON r.movie_id = m.id
            ORDER BY r.created_at DESC
            LIMIT %s
            """
            cursor.execute(sql, (limit,))
            reviews = cursor.fetchall()
            
        return reviews
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения отзывов: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.get("/reviews/user/{user_name}", response_model=List[models.Review])
async def get_user_reviews(user_name: str):
    """
    Получить все отзывы пользователя
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            SELECT r.*, m.title as movie_title
            FROM reviews r
            JOIN movies m ON r.movie_id = m.id
            WHERE r.user_name ILIKE %s
            ORDER BY r.created_at DESC
            """
            cursor.execute(sql, (user_name,))
            reviews = cursor.fetchall()
            
        return reviews
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения отзывов: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.delete("/reviews/{review_id}", response_model=dict)
async def delete_review(review_id: int):
    """
    Удалить отзыв
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM reviews WHERE id = %s", (review_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Отзыв не найден")
            
            cursor.execute("DELETE FROM reviews WHERE id = %s", (review_id,))
            connection.commit()
            
        return {"message": "Отзыв успешно удален"}
    
    except HTTPException:
        raise
    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления отзыва: {str(e)}")
    
    finally:
        if connection:
            connection.close()