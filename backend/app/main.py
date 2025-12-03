from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # 记得导入这个

from app.core.config import get_settings
from app.core.database import init_db, shutdown_db
from app.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await shutdown_db()

def create_app() -> FastAPI:
    settings = get_settings()
    # 1. 创建 app 实例
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    
    # 2. 【关键修正】在这里添加 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 允许所有来源
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. 注册路由
    app.include_router(api_router, prefix=settings.api_prefix)
    
    return app

# 生成最终的 app 实例
app = create_app()