# from fastcgan.routes import router
from fastapi import APIRouter

from fastcgan.tools.config import settings
from fastcgan.tools.setup import create_application

app = create_application(router=APIRouter(prefix="/api"), settings=settings)
