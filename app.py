from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Book
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def index():
    genre = request.args.get("genre")
    search = request.args.get("search", "").strip()

    query = Book.query
    if genre:
        query = query.filter_by(genre=genre)
    if search:
        query = query.filter(
            Book.title.ilike(f"%{search}%") | Book.author.ilike(f"%{search}%")
        )

    books = query.order_by(Book.year.desc()).all()
    genres = db.session.query(Book.genre).distinct().order_by(Book.genre).all()
    genres = [g[0] for g in genres]

    return render_template(
        "index.html", books=books, genres=genres, current_genre=genre, search=search
    )


@app.route("/book/<int:book_id>")
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template("book_detail.html", book=book)


@app.route("/add", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        genre = request.form.get("genre", "").strip()
        year = request.form.get("year", "").strip()
        description = request.form.get("description", "").strip()

        if not title or not author or not genre or not year:
            flash("Заполните все обязательные поля", "error")
            return redirect(url_for("add_book"))

        try:
            year = int(year)
        except ValueError:
            flash("Год должен быть числом", "error")
            return redirect(url_for("add_book"))

        book = Book(
            title=title, author=author, genre=genre, year=year, description=description
        )
        db.session.add(book)
        db.session.commit()
        flash("Книга добавлена", "success")
        return redirect(url_for("index"))

    return render_template("add_book.html")


@app.route("/edit/<int:book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)

    if request.method == "POST":
        book.title = request.form.get("title", "").strip()
        book.author = request.form.get("author", "").strip()
        book.genre = request.form.get("genre", "").strip()
        book.description = request.form.get("description", "").strip()

        try:
            book.year = int(request.form.get("year", "").strip())
        except ValueError:
            flash("Год должен быть числом", "error")
            return redirect(url_for("edit_book", book_id=book_id))

        db.session.commit()
        flash("Книга обновлена", "success")
        return redirect(url_for("book_detail", book_id=book_id))

    return render_template("edit_book.html", book=book)


@app.route("/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash("Книга удалена", "success")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(e):
    return render_template("base.html", error="Страница не найдена"), 404


if __name__ == "__main__":
    app.run(debug=True)
