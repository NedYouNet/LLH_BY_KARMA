from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ваши импорты
import routers  # Парсинг резюме (название вашего файла)
import router_tasks  # Генерация задач
import router_grader # Наш новый автогрейдер

app = FastAPI(title="FSP Hackathon ML API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routers.router)
app.include_router(router_tasks.router)
# Подключаем грейдер
app.include_router(router_grader.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)