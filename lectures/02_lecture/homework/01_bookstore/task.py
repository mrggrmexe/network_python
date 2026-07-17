"""
01_bookstore — CRUD API для книжного магазина 📚

Спроектируйте REST API для управления каталогом книг.

Спецификация эндпоинтов (ничего не менять — тесты завязаны на них):

    GET    /books              — список книг (с опциональной фильтрацией)
    GET    /books/{id}         — одна книга по id
    POST   /books              — создать книгу
    PUT    /books/{id}         — полностью обновить книгу
    DELETE /books/{id}         — удалить книгу
    GET    /books/search       — поиск книг по названию или автору

    # Дополнительно — категории
    GET    /categories         — список категорий
    POST   /categories         — создать категорию

Требования к реализации:
    1. Используйте FastAPI + Pydantic
    2. Храните данные в памяти (глобальный список/словарь)
    3. Правильные HTTP-статусы:
        - 200 — успешный GET, PUT
        - 201 — успешный POST
        - 204 — успешный DELETE
        - 404 — ресурс не найден
        - 409 — конфликт (например, дубликат)
        - 422 — невалидные данные (Pydantic сам это делает)
    4. Валидация полей через Pydantic Field:
        - title:  не пустой, до 100 символов
        - author: не пустой, до 100 символов
        - year:   ≥ 0, до 2025
        - isbn:   строка 10 или 13 цифр (978-5-xxx...)
        - price:  > 0
        - category_id: опционально, ссылка на категорию
    5. Кастомная обработка ошибок:
        - BookNotFoundException → 404 c {"detail": "Book not found", "code": "NOT_FOUND"}
        - DuplicateIsbnException → 409 c {"detail": "...", "code": "DUPLICATE_ISBN"}
    6. Поиск /books/search?query=... — ищет по title и author (case-insensitive)
    7. Фильтрация GET /books?category_id=N&year=2024
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

# ═══════════════════════════════════════════════════════════
# МОДЕЛИ
# ═══════════════════════════════════════════════════════════


class Category(BaseModel):
    """Доменная модель категории. Возвращается в ответах."""

    id: int
    name: str = Field(min_length=1, max_length=50)


class CategoryCreate(BaseModel):
    """Модель для создания категории (без id, лишние поля запрещены)."""

    name: str = Field(min_length=1, max_length=50)

    model_config = {"extra": "forbid"}


class Book(BaseModel):
    """Доменная модель книги. Возвращается в ответах GET/PUT."""

    id: int
    title: str = Field(min_length=1, max_length=100)
    author: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=0, le=2025)
    isbn: str = Field(pattern=r"^\d{10}(?:\d{3})?$")
    price: float = Field(gt=0)
    category_id: Optional[int] = None


class BookCreate(BaseModel):
    """Модель для создания/обновления книги (без id — сервер сгенерирует)."""

    title: str = Field(min_length=1, max_length=100)
    author: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=0, le=2025)
    isbn: str = Field(pattern=r"^\d{10}(?:\d{3})?$")
    price: float = Field(gt=0)
    category_id: Optional[int] = None


# ═══════════════════════════════════════════════════════════
# ИСКЛЮЧЕНИЯ
# ═══════════════════════════════════════════════════════════


class BookNotFoundException(HTTPException):
    """404 — книга не найдена."""

    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")


class DuplicateIsbnException(HTTPException):
    """409 — ISBN уже существует."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="ISBN already exists",
        )


# ═══════════════════════════════════════════════════════════
# ПРИЛОЖЕНИЕ
# ═══════════════════════════════════════════════════════════

app = FastAPI(title="Bookstore API")

# Хранилище
BOOKS: list[dict] = []
CATEGORIES: list[dict] = []


def reset_storage() -> None:
    """Очистить хранилище; используется fixture'ами для изоляции тестов."""
    BOOKS.clear()
    CATEGORIES.clear()


def _next_id(items: list[dict]) -> int:
    return max((item["id"] for item in items), default=0) + 1


def _get_book_or_raise(book_id: int) -> dict:
    for stored_book in BOOKS:
        if stored_book["id"] == book_id:
            return stored_book
    raise BookNotFoundException()


@app.exception_handler(BookNotFoundException)
def book_not_found_handler(
    request: Request, exc: BookNotFoundException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": "NOT_FOUND"},
    )


@app.exception_handler(DuplicateIsbnException)
def duplicate_isbn_handler(
    request: Request, exc: DuplicateIsbnException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": "DUPLICATE_ISBN"},
    )


# ═══════════════════════════════════════════════════════════
# КАТЕГОРИИ
# ═══════════════════════════════════════════════════════════


@app.get("/categories")
def list_categories():
    """GET /categories — список всех категорий."""
    return CATEGORIES


@app.post("/categories", status_code=201)
def create_category(category: CategoryCreate):
    """POST /categories — создать категорию."""
    created_category = {"id": _next_id(CATEGORIES), **category.model_dump()}
    CATEGORIES.append(created_category)
    return created_category


# ═══════════════════════════════════════════════════════════
# CRUID КНИГ
# ═══════════════════════════════════════════════════════════


@app.get("/books")
def list_books(category_id: Optional[int] = None, year: Optional[int] = None):
    """GET /books — список книг. Опциональная фильтрация по category_id и year."""
    return [
        book
        for book in BOOKS
        if (category_id is None or book["category_id"] == category_id)
        and (year is None or book["year"] == year)
    ]


@app.get("/books/search")
def search_books(query: str):
    """GET /books/search?query=... — поиск по title и author (case-insensitive)."""
    normalized_query = query.casefold()
    return [
        book
        for book in BOOKS
        if normalized_query in book["title"].casefold()
        or normalized_query in book["author"].casefold()
    ]


@app.get("/books/{book_id}")
def get_book(book_id: int):
    """GET /books/{id} — одна книга."""
    return _get_book_or_raise(book_id)


@app.post("/books", status_code=201)
def create_book(book: BookCreate):
    """POST /books — создать книгу.

    Проверять уникальность ISBN. Если дубликат — DuplicateIsbnException.
    """
    if any(stored_book["isbn"] == book.isbn for stored_book in BOOKS):
        raise DuplicateIsbnException()

    created_book = {"id": _next_id(BOOKS), **book.model_dump()}
    BOOKS.append(created_book)
    return created_book


@app.put("/books/{book_id}")
def update_book(book_id: int, book: BookCreate):
    """PUT /books/{id} — полностью обновить книгу."""
    stored_book = _get_book_or_raise(book_id)
    if any(
        other_book["id"] != book_id and other_book["isbn"] == book.isbn
        for other_book in BOOKS
    ):
        raise DuplicateIsbnException()

    stored_book.update(book.model_dump())
    return stored_book


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    """DELETE /books/{id} — удалить книгу."""
    stored_book = _get_book_or_raise(book_id)
    BOOKS.remove(stored_book)
