"""Тесты веб-интерфейса и CRUD-операций."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import Book


class TestApp(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_book(self, title='Test Book', author='Author', genre='Fiction', year=2020):
        with app.app_context():
            book = Book(title=title, author=author, genre=genre, year=year)
            db.session.add(book)
            db.session.commit()
            return book.id

    def test_index_empty(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_index_with_books(self):
        self._create_book()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Book', response.data)

    def test_book_detail(self):
        book_id = self._create_book()
        response = self.client.get(f'/book/{book_id}')
        self.assertEqual(response.status_code, 200)

    def test_book_detail_404(self):
        response = self.client.get('/book/99999')
        self.assertEqual(response.status_code, 404)

    def test_add_book_get(self):
        response = self.client.get('/add')
        self.assertEqual(response.status_code, 200)

    def test_add_book_post_success(self):
        response = self.client.post('/add', data={
            'title': 'New Book',
            'author': 'New Author',
            'genre': 'Sci-Fi',
            'year': '2025',
            'description': 'Test'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_add_book_post_empty_title(self):
        response = self.client.post('/add', data={
            'title': '',
            'author': 'Author',
            'genre': 'Fiction',
            'year': '2020'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_edit_book(self):
        book_id = self._create_book()
        response = self.client.post(f'/edit/{book_id}', data={
            'title': 'Updated Book',
            'author': 'Author',
            'genre': 'Fiction',
            'year': '2021',
            'description': ''
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_delete_book(self):
        book_id = self._create_book()
        response = self.client.post(f'/delete/{book_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_search(self):
        self._create_book(title='Python Programming')
        response = self.client.get('/?search=Python')
        self.assertEqual(response.status_code, 200)

    def test_filter_by_genre(self):
        self._create_book(genre='Sci-Fi')
        response = self.client.get('/?genre=Sci-Fi')
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()