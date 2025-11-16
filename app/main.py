from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
import os

from app.routers import movies, reviews, users
from app.database import init_db, test_connection, get_db_connection

os.makedirs("templates", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)

app = FastAPI(
    title="🎬 Movie Reviews API",
    description="Система рецензий на фильмы с веб-интерфейсом и API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup_event():
    print("Запуск Movie Reviews API...")
    if test_connection():
        print("Подключение к базе данных успешно")
        init_db()
    else:
        print(" Не удалось подключиться к базе данных")
    
    print("Приложение готово к работе")

# Подключаем роутеры
app.include_router(movies.router, prefix="/api/v1", tags=["movies"])
app.include_router(reviews.router, prefix="/api/v1", tags=["reviews"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])

# Веб-эндпоинты для HTML страниц
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Главная страница со списком фильмов"""
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            SELECT m.id, m.title, m.director, m.release_year, m.genre,
                   COALESCE(AVG(r.rating), 0) as avg_rating,
                   COUNT(r.id) as review_count
            FROM movies m
            LEFT JOIN reviews r ON m.id = r.movie_id
            GROUP BY m.id, m.title, m.director, m.release_year, m.genre
            ORDER BY avg_rating DESC
            """
            cursor.execute(sql)
            movies_tuples = cursor.fetchall()
            
            # Преобразуем кортежи в словари
            movies_list = []
            for movie in movies_tuples:
                movies_list.append({
                    'id': movie[0],
                    'title': movie[1],
                    'director': movie[2],
                    'release_year': movie[3],
                    'genre': movie[4],
                    'avg_rating': round(float(movie[5] or 0), 1),
                    'review_count': movie[6]
                })
            
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "movies": movies_list
        })
    
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Ошибка сервера: {str(e)}"
        })
    
    finally:
        if connection:
            connection.close()

@app.get("/add-movie", response_class=HTMLResponse)
async def add_movie_form(request: Request):
    """Форма добавления нового фильма"""
    return templates.TemplateResponse("add_movie.html", {
        "request": request
    })

@app.post("/add-movie")
async def add_movie_submit(
    request: Request,
    title: str = Form(...),
    director: str = Form(...),
    release_year: int = Form(None),
    genre: str = Form(None),
    description: str = Form(None)
):
    """Обработка формы добавления фильма"""
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO movies (title, director, release_year, genre, description)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """
            cursor.execute(sql, (
                title.strip(),
                director.strip(),
                release_year,
                genre if genre else None,
                description.strip() if description else None
            ))
            
            movie_id = cursor.fetchone()[0]
            connection.commit()
            
        return RedirectResponse(url=f"/movies/{movie_id}", status_code=303)
    
    except Exception as e:
        if connection:
            connection.rollback()
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Ошибка добавления фильма: {str(e)}"
        })
    
    finally:
        if connection:
            connection.close()

@app.get("/movies/{movie_id}", response_class=HTMLResponse)
async def get_movie_detail(request: Request, movie_id: int):
    """Страница фильма с детальной информацией и отзывами"""
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Получаем информацию о фильме
            cursor.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
            movie_tuple = cursor.fetchone()
            
            if not movie_tuple:
                return templates.TemplateResponse("error.html", {
                    "request": request,
                    "error": "Фильм не найден"
                })
            
            # Преобразуем кортеж в словарь
            movie = {
                'id': movie_tuple[0],
                'title': movie_tuple[1],
                'director': movie_tuple[2],
                'release_year': movie_tuple[3],
                'genre': movie_tuple[4],
                'description': movie_tuple[5]
            }
            
            # Получаем отзывы
            cursor.execute("""
                SELECT * FROM reviews 
                WHERE movie_id = %s 
                ORDER BY created_at DESC
            """, (movie_id,))
            reviews_tuples = cursor.fetchall()
            
            # Преобразуем отзывы
            reviews_list = []
            for review in reviews_tuples:
                reviews_list.append({
                    'id': review[0],
                    'movie_id': review[1],
                    'user_name': review[2],
                    'rating': review[3],
                    'review_text': review[4],
                    'created_at': review[5]
                })
            
            # Средний рейтинг и количество отзывов
            cursor.execute("""
                SELECT AVG(rating) as avg_rating, COUNT(*) as review_count 
                FROM reviews WHERE movie_id = %s
            """, (movie_id,))
            stats = cursor.fetchone()
            movie['avg_rating'] = round(float(stats[0] or 0), 1)
            movie['review_count'] = stats[1]
            
        return templates.TemplateResponse("movie_detail.html", {
            "request": request,
            "movie": movie,
            "reviews": reviews_list
        })
    
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Ошибка сервера: {str(e)}"
        })
    
    finally:
        if connection:
            connection.close()

# Исправленный эндпоинт для добавления отзыва
@app.post("/movies/{movie_id}/review")
async def add_review_web(
    request: Request,
    movie_id: int,
    user_name: str = Form(...),
    rating: int = Form(...),
    review_text: str = Form("")
):
    """Добавить отзыв через веб-форму"""
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Проверяем существование фильма
            cursor.execute("SELECT id FROM movies WHERE id = %s", (movie_id,))
            if not cursor.fetchone():
                return templates.TemplateResponse("error.html", {
                    "request": request,
                    "error": "Фильм не найден"
                })
            
            # Добавляем отзыв
            sql = """
            INSERT INTO reviews (movie_id, user_name, rating, review_text) 
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (
                movie_id, 
                user_name.strip(), 
                rating, 
                review_text.strip() or None
            ))
            connection.commit()
            
        return RedirectResponse(url=f"/movies/{movie_id}", status_code=303)
    
    except Exception as e:
        if connection:
            connection.rollback()
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Ошибка добавления отзыва: {str(e)}"
        })
    
    finally:
        if connection:
            connection.close()

# API эндпоинты (минимальные требования)
@app.get("/movies", response_class=HTMLResponse)
async def get_all_movies_web(request: Request):
    """GET /movies - список всех фильмов с средним рейтингом"""
    return await read_root(request)

@app.get("/movies/{movie_id}/reviews", response_class=HTMLResponse)
async def get_movie_reviews_web(request: Request, movie_id: int):
    """GET /movies/{id}/reviews - получить все отзывы по фильму"""
    return await get_movie_detail(request, movie_id)

@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"}
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=404,
        content={"detail": "Ресурс не найден"}
    )

@app.get("/api")
async def root():
    return {"message": "Movie Reviews API", "version": "1.0.0"}