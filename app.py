# fastapi_app.py
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiohttp
from typing import Literal, Any
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import re
import asyncio
from dotenv import load_dotenv
import os

# Настройки базы данных
DATABASE_URL = "postgresql+psycopg2://postgres:artas@localhost/uproject-users"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

load_dotenv()
LOLZTOKEN = os.getenv("LOLZTOKEN")
print(LOLZTOKEN)

# Создаем экземпляр FastAPI
app = FastAPI()

# Разрешаем CORS для всех источников
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все домены, вы можете указать конкретные
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все HTTP методы
    allow_headers=["*"],  # Разрешаем все заголовки
)

# Модель таблицы Users
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)

# Создать таблицы, если их нет
Base.metadata.create_all(bind=engine)

# Pydantic модель для валидации запросов
class UserCreate(BaseModel):
    username: str

# Эндпоинт: Получить всех пользователей
@app.get("/users")
def get_users():
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    return users

# Эндпоинт: Создать пользователя
@app.post("/users")
def create_user(user: UserCreate):
    db = SessionLocal()
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        db.close()
        raise HTTPException(status_code=400, detail="Пользователь уже присутствует")
    new_user = User(username=user.username)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()
    return new_user

# Модель для обработки ссылок
class LinksRequest(BaseModel):
    links: list[str]

# Функция для получения информации по товару
async def get_item_info(item_id, item_type="default"):
    base_url = "https://api.zelenka.guru/market"
    url = f"{base_url}/{item_id}?oauth_token={LOLZTOKEN}"
    
    if item_type == "special":
        url = f"{base_url}/{item_id}/special?oauth_token={LOLZTOKEN}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    item_info = await response.json()
                    item_info = item_info["item"]
                    price = item_info["price"]
                    item_state = item_info["item_state"]

                    if item_state == "paid":
                        grnt_active = item_info.get("guarantee", {}).get("active", False)
                        return price, grnt_active, item_state
                    elif item_state == "active":
                        return price, item_state
                elif response.status == 429:
                    print(f"2 секунды")
                    await asyncio.sleep(2)  # Задержка на 2 секунды
                    return await get_item_info(item_id, item_type)  # Повторить запрос
                else:
                    print(f"Failed request with status: {response.status}")
                    return None
        except Exception as e:
            print(f"Error occurred: {e}")
            return None

# Эндпоинт: Обработка ссылок
@app.post("/process-links")
async def process_links(request: LinksRequest):
    links = request.links
    result = ""

    for link in links:
        item_id = ''.join(filter(str.isdigit, link))
        item_info = await get_item_info(item_id)

        if item_info:
            # Если item_info возвращает меньше 3 значений, присваиваем значения по умолчанию
            if len(item_info) == 3:
                original_price, grnt_active, item_state = item_info
            elif len(item_info) == 2:
                original_price, item_state = item_info
            else:
                result += f"Ошибка обработки аккаунта: {link}\n"
                print(f"Неожиданный формат данных для ссылки: {link}")
                continue

            discounted_price = round(float(original_price) * 0.97)

            # Преобразуем состояние в текст
            if item_state == "paid":
                item_state = "🟢"
                if grnt_active:  # Проверяем активность гарантии
                    item_state = "🟡"
            if item_state == "active":
                item_state = "🔴"
            result += f"Аккаунт: {link} - Состояние: {item_state}, Цена: {discounted_price}\n"
        else:
            result += f"Удалено/Нет доступа: {link}\n"
            print(f"Удалено/Нет доступа: {link}")  # Логируем ошибку

    return {"message": result}


# Запуск FastAPI сервера
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
