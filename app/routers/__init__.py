from .movies import router as movies_router
from .reviews import router as reviews_router 
from .users import router as users_router

__all__ = ["movies_router", "reviews_router", "users_router"]