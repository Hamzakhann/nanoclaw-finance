import os
from datetime import datetime, date
from decimal import Decimal

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Date,
    DateTime,
    ForeignKey,
    DECIMAL,
)
from sqlalchemy.orm import declarative_base, relationship

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    expenses = relationship("Expense", back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.name!r} email={self.email!r}>"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500), nullable=True)

    expenses = relationship("Expense", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(DECIMAL(10, 2), nullable=False)
    description = Column(String(500), nullable=False)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    category = relationship("Category", back_populates="expenses")
    user = relationship("User", back_populates="expenses")

    def __repr__(self) -> str:
        return (
            f"<Expense id={self.id} amount=PKR {self.amount:,.2f}"
            f" date={self.date} category_id={self.category_id}>"
        )


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Tables created against:", DATABASE_URL)
