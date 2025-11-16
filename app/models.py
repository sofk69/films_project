from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class Genre(str, Enum):
    """Жанры фильмов"""
    ACTION = "Боевик"
    COMEDY = "Комедия"
    DRAMA = "Драма"
    FANTASY = "Фантастика"
    HORROR = "Ужасы"
    ROMANCE = "Мелодрама"
    THRILLER = "Триллер"
    CRIME = "Криминал"
    ADVENTURE = "Приключения"
    ANIMATION = "Анимация"
    DOCUMENTARY = "Документальный"

class ReviewBase(BaseModel):
    """Базовая модель отзыва"""
    user_name: str = Field(..., min_length=1, max_length=100, description="Имя пользователя")
    rating: int = Field(..., ge=1, le=10, description="Оценка от 1 до 10")
    review_text: Optional[str] = Field(None, max_length=1000, description="Текст отзыва")

    @validator('user_name')
    def validate_user_name(cls, v):
        if not v.strip():
            raise ValueError('Имя пользователя не может быть пустым')
        return v.strip()

    @validator('review_text')
    def validate_review_text(cls, v):
        if v and len(v.strip()) == 0:
            return None
        return v

class ReviewCreate(ReviewBase):
    """Модель для создания отзыва"""
    movie_id: int = Field(..., gt=0, description="ID фильма")

class Review(ReviewBase):
    """Модель отзыва с ID и датой"""
    id: int
    movie_id: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class MovieBase(BaseModel):
    """Базовая модель фильма"""
    title: str = Field(..., min_length=1, max_length=255, description="Название фильма")
    director: str = Field(..., min_length=1, max_length=255, description="Режиссер")
    release_year: Optional[int] = Field(None, ge=1888, le=2100, description="Год выпуска")
    genre: Optional[Genre] = Field(None, description="Жанр фильма")
    description: Optional[str] = Field(None, max_length=2000, description="Описание фильма")
    duration_minutes: Optional[int] = Field(None, ge=1, le=500, description="Продолжительность в минутах")

    @validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Название фильма не может быть пустым')
        return v.strip()

    @validator('director')
    def validate_director(cls, v):
        if not v.strip():
            raise ValueError('Имя режиссера не может быть пустым')
        return v.strip()

class MovieCreate(MovieBase):
    """Модель для создания фильма"""
    pass

class Movie(MovieBase):
    """Модель фильма с ID и статистикой"""
    id: int
    avg_rating: Optional[float] = None
    review_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class MovieWithReviews(Movie):
    """Модель фильма с отзывами"""
    reviews: List[Review] = []

class MovieUpdate(BaseModel):
    """Модель для обновления фильма"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    director: Optional[str] = Field(None, min_length=1, max_length=255)
    release_year: Optional[int] = Field(None, ge=1888, le=2100)
    genre: Optional[Genre] = None
    description: Optional[str] = Field(None, max_length=2000)
    duration_minutes: Optional[int] = Field(None, ge=1, le=500)

class UserBase(BaseModel):
    """Базовая модель пользователя"""
    username: str = Field(..., min_length=3, max_length=50, description="Имя пользователя")
    email: str = Field(..., description="Email адрес")

class UserCreate(UserBase):
    """Модель для создания пользователя"""
    pass

class User(UserBase):
    """Модель пользователя"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    """Модель для статистики"""
    total_movies: int
    total_reviews: int
    average_rating: float
    top_genre: Optional[str]
    most_reviewed_movie: Optional[str]
    total_users: int

class SearchResponse(BaseModel):
    """Модель для ответа поиска"""
    query: str
    results: List[Movie]
    total_count: int