from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Импортируем наши изолированные роутеры
from routers.matching import router as matching_router
from routers.parsing import router as parsing_router
# Позже напарник добавит свой: from routers.testing import router as testing_router

app = FastAPI(title="FSP IT Platform API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(matching_router)
app.include_router(parsing_router)
# app.include_router(testing_router)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "FSP IT Platform API is running"}