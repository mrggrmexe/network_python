"""
02_errors_and_tests — чиним и тестируем 🛠️

В app.py лежит сломанное FastAPI-приложение. Найдите и исправьте ВСЕ проблемы.

Задача А: Исправить приложение (task.py)
    Скопируйте app.py сюда и исправьте все ошибки.
    Внимание: tests будут проверять ВАШУ реализацию, не оригинальный app.py.

    Чего ждут тесты:
        ✓ POST /items → 201 Created
        ✓ GET  /items/{id} → 200 или 404
        ✓ PUT  /items/{id} → 200 или 404
        ✓ DELETE /items/{id} → 204 или 404
        ✓ GET  /divide?a=10&b=0 → 400 (не 500!)
        ✓ GET  /items/{id}/counter → race condition отсутствует
        ✓ GET  /slow-sync → async def + await asyncio.sleep
        ✓ DELETE возвращает правильный статус (204)

Задача Б: Написать тесты в test_errors.py
    Покрыть все эндпоинты.
"""

import asyncio
from threading import Lock

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI()

ITEMS: dict[int, dict] = {}
NEXT_ID = 1
COUNTER = 0
COUNTER_LOCK = Lock()


class ItemCreate(BaseModel):
    name: str


class ItemUpdate(BaseModel):
    name: str = ""


# ═══════════════════════════════════════════════════════════
# ИСПРАВЛЯЙТЕ НИЖЕ
# ═══════════════════════════════════════════════════════════


def reset_storage() -> None:
    """Очистить хранилище; используется fixture'ами для изоляции тестов."""
    global NEXT_ID, COUNTER
    ITEMS.clear()
    NEXT_ID = 1
    COUNTER = 0


def _get_item_or_raise(item_id: int) -> dict:
    try:
        return ITEMS[item_id]
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        ) from error


@app.get("/items")
def list_items():
    return {"items": list(ITEMS.values())}


@app.get("/items/{item_id}")
def get_item(item_id: int):
    return _get_item_or_raise(item_id)


@app.post("/items", status_code=201)
def create_item(item: ItemCreate):
    global NEXT_ID
    created_item = {"id": NEXT_ID, "name": item.name}
    ITEMS[NEXT_ID] = created_item
    NEXT_ID += 1
    return created_item


@app.get("/items/{item_id}/counter")
def get_counter(item_id: int):
    _get_item_or_raise(item_id)
    global COUNTER
    with COUNTER_LOCK:
        COUNTER += 1
        return {"counter": COUNTER}


@app.put("/items/{item_id}")
def update_item(item_id: int, update: ItemUpdate):
    item = _get_item_or_raise(item_id)
    item["name"] = update.name
    return item


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int):
    _get_item_or_raise(item_id)
    del ITEMS[item_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/divide")
def divide(a: int, b: int):
    if b == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Division by zero is not allowed",
        )
    return {"result": a / b}


@app.get("/slow-sync")
async def slow_sync():
    await asyncio.sleep(0.5)
    return {"status": "done"}
