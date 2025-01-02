from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Настройки базы данных
DATABASE_URL = "postgresql+psycopg2://postgres:artas@localhost/uproject-users"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Создаем экземпляр FastAPI
app = FastAPI()

# Разрешаем CORS для всех источников (или только для нужного домена)
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
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = User(username=user.username)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()
    return new_user
