# from fastcgan.routes import router
from fastapi import APIRouter

from fastcgan.config import settings
from fastcgan.setup import create_application

app = create_application(router=APIRouter(prefix="/api"), settings=settings)
