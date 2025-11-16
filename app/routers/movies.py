from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from typing import List, Optional
import app.database as database
import app.models as models

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Главная страница - список всех фильмов
    """
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            SELECT m.*, 
                   COALESCE(AVG(r.rating), 0) as avg_rating,
                   COUNT(r.id) as review_count
            FROM movies m
            LEFT JOIN reviews r ON m.id = r.movie_id
            GROUP BY m.id
            ORDER BY avg_rating DESC NULLS LAST
            """
            cursor.execute(sql)
            movies = cursor.fetchall()
            
            for movie in movies:
                movie['avg_rating'] = round(float(movie['avg_rating'] or 0), 1)
                movie['release_year'] = movie['release_year'] or 'Не указан'
                movie['duration_minutes'] = movie['duration_minutes'] or 'Не указана'
            
        return models.templates.TemplateResponse("index.html", {
            "request": request, 
            "movies": movies
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.get("/movies", response_model=List[models.Movie])
async def get_movies(
    skip: int = Query(0, ge=0, description="Пропустить записей"),
    limit: int = Query(100, ge=1, le=1000, description="Лимит записей"),
    genre: Optional[models.Genre] = Query(None, description="Фильтр по жанру")
):
    """
    Получить список всех фильмов с пагинацией
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            where_clause = "WHERE m.genre = %s" if genre else ""
            params = [genre.value] if genre else []
            
            sql = f"""
            SELECT m.*, 
                   COALESCE(AVG(r.rating), 0) as avg_rating,
                   COUNT(r.id) as review_count
            FROM movies m
            LEFT JOIN reviews r ON m.id = r.movie_id
            {where_clause}
            GROUP BY m.id
            ORDER BY m.title
            LIMIT %s OFFSET %s
            """
            params.extend([limit, skip])
            
            cursor.execute(sql, params)
            movies = cursor.fetchall()
            
            for movie in movies:
                movie['avg_rating'] = float(movie['avg_rating'])
            
        return movies
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.get("/movies/search", response_model=models.SearchResponse)
async def search_movies(
    q: str = Query(..., min_length=2, max_length=100, description="Поисковый запрос"),
    limit: int = Query(20, ge=1, le=100, description="Лимит результатов")
):
    """
    Поиск фильмов по названию, режиссеру или жанру
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            SELECT m.*, 
                   COALESCE(AVG(r.rating), 0) as avg_rating,
                   COUNT(r.id) as review_count
            FROM movies m
            LEFT JOIN reviews r ON m.id = r.movie_id
            WHERE m.title ILIKE %s OR m.director ILIKE %s OR m.genre ILIKE %s
            GROUP BY m.id
            ORDER BY avg_rating DESC NULLS LAST
            LIMIT %s
            """
            search_term = f"%{q}%"
            cursor.execute(sql, (search_term, search_term, search_term, limit))
            movies = cursor.fetchall()
            
            for movie in movies:
                movie['avg_rating'] = float(movie['avg_rating'])
            
            count_sql = """
            SELECT COUNT(DISTINCT m.id) as total_count
            FROM movies m
            WHERE m.title ILIKE %s OR m.director ILIKE %s OR m.genre ILIKE %s
            """
            cursor.execute(count_sql, (search_term, search_term, search_term))
            total_count = cursor.fetchone()['total_count']
            
        return models.SearchResponse(
            query=q,
            results=movies,
            total_count=total_count
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.get("/movies/{movie_id}", response_class=HTMLResponse)
async def get_movie_detail(request: Request, movie_id: int):
    """
    Страница фильма с детальной информацией и отзывами
    """
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
            movie = cursor.fetchone()
            
            if not movie:
                raise HTTPException(status_code=404, detail="Фильм не найден")
            
            cursor.execute("""
                SELECT * FROM reviews 
                WHERE movie_id = %s 
                ORDER BY created_at DESC
            """, (movie_id,))
            reviews = cursor.fetchall()
            
            cursor.execute("SELECT AVG(rating) as avg_rating FROM reviews WHERE movie_id = %s", (movie_id,))
            avg_result = cursor.fetchone()
            movie['avg_rating'] = round(float(avg_result['avg_rating'] or 0), 1)
            movie['review_count'] = len(reviews)
            
        return models.templates.TemplateResponse("movie_detail.html", {
            "request": request,
            "movie": movie,
            "reviews": reviews
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.get("/movies/{movie_id}/info", response_model=models.Movie)
async def get_movie_info(movie_id: int):
    """
    Получить информацию о фильме по ID (API)
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            SELECT m.*, 
                   COALESCE(AVG(r.rating), 0) as avg_rating,
                   COUNT(r.id) as review_count
            FROM movies m
            LEFT JOIN reviews r ON m.id = r.movie_id
            WHERE m.id = %s
            GROUP BY m.id
            """
            cursor.execute(sql, (movie_id,))
            movie = cursor.fetchone()
            
            if not movie:
                raise HTTPException(status_code=404, detail="Фильм не найден")
            
            movie['avg_rating'] = float(movie['avg_rating'])
            
        return movie
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.post("/movies", response_model=dict)
async def create_movie(movie: models.MovieCreate):
    """
    Создать новый фильм
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO movies (title, director, release_year, genre, description, duration_minutes)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """
            cursor.execute(sql, (
                movie.title,
                movie.director,
                movie.release_year,
                movie.genre.value if movie.genre else None,
                movie.description,
                movie.duration_minutes
            ))
            movie_id = cursor.fetchone()['id']
            connection.commit()
            
        return {"message": "Фильм успешно создан", "movie_id": movie_id}
    
    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания фильма: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.put("/movies/{movie_id}", response_model=dict)
async def update_movie(movie_id: int, movie_update: models.MovieUpdate):
    """
    Обновить информацию о фильме
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM movies WHERE id = %s", (movie_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Фильм не найден")
            
            update_fields = []
            params = []
            
            if movie_update.title is not None:
                update_fields.append("title = %s")
                params.append(movie_update.title)
            if movie_update.director is not None:
                update_fields.append("director = %s")
                params.append(movie_update.director)
            if movie_update.release_year is not None:
                update_fields.append("release_year = %s")
                params.append(movie_update.release_year)
            if movie_update.genre is not None:
                update_fields.append("genre = %s")
                params.append(movie_update.genre.value)
            if movie_update.description is not None:
                update_fields.append("description = %s")
                params.append(movie_update.description)
            if movie_update.duration_minutes is not None:
                update_fields.append("duration_minutes = %s")
                params.append(movie_update.duration_minutes)
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="Нет данных для обновления")
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(movie_id)
            
            sql = f"UPDATE movies SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(sql, params)
            connection.commit()
            
        return {"message": "Фильм успешно обновлен"}
    
    except HTTPException:
        raise
    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка обновления фильма: {str(e)}")
    
    finally:
        if connection:
            connection.close()

@router.delete("/movies/{movie_id}", response_model=dict)
async def delete_movie(movie_id: int):
    """
    Удалить фильм
    """
    connection = None
    try:
        connection = database.get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM movies WHERE id = %s", (movie_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Фильм не найден")
            
            cursor.execute("DELETE FROM movies WHERE id = %s", (movie_id,))
            connection.commit()
            
        return {"message": "Фильм успешно удален"}
    
    except HTTPException:
        raise
    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления фильма: {str(e)}")
    
    finally:
        if connection:
            connection.close()