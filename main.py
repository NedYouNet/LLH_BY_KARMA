from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
# Импортируем ваши роутеры (укажите реальные названия ваших файлов без .py)
# Например, если файл называется routers_3.py, пишем import routers_3
import routers
import router_tasks

app = FastAPI(title="FSP Hackathon ML API")

# Настройка CORS для работы с React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры к приложению
app.include_router(routers.router)
app.include_router(router_tasks.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)