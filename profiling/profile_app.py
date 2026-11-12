"""Скрипт профилирования Flask-приложения."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db, Book


@profile
def load_index():
    """Имитирует запрос к главной странице."""
    with app.test_client() as client:
        response = client.get('/')
        return response.status_code


if __name__ == '__main__':
    with app.app_context():
        # Создаём тестовые данные, если их нет
        if Book.query.count() == 0:
            for i in range(100):
                book = Book(
                    title=f'Книга {i}',
                    author=f'Автор {i}',
                    genre='Тест',
                    year=2000 + (i % 20)
                )
                db.session.add(book)
            db.session.commit()
            print(f'Создано {Book.query.count()} тестовых записей')
        
        # Вызываем профилируемую функцию
        status = load_index()
        print(f'Статус ответа: {status}')