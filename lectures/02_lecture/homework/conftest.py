"""Общие фикстуры и настройки pytest для домашних заданий."""

import sys

import pytest


def pytest_configure(config):
    """Регистрация кастомных маркеров."""
    config.addinivalue_line(
        "markers",
        "slow: медленные тесты. Запускать отдельно: pytest -m slow",
    )


def pytest_report_header(config):
    return [
        "Домашние задания — Лекция 2: REST API, HTTP, FastAPI",
        "Ожидания: все тесты должны быть зелёными ✅",
    ]


@pytest.fixture(autouse=True)
def reset_in_memory_storages():
    """Не позволять данным одного теста влиять на другой."""
    for module in tuple(sys.modules.values()):
        module_file = getattr(module, "__file__", "") or ""
        if module_file.endswith(("01_bookstore/task.py", "02_errors_and_tests/task.py")):
            module.reset_storage()
