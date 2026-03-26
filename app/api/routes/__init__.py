from fastapi import APIRouter

from app.api.routes import auth, services, bookings, provider, payments, reviews

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(services.router)
api_router.include_router(bookings.router)
api_router.include_router(provider.router)
api_router.include_router(payments.router)
api_router.include_router(reviews.router)