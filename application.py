import os

from flask import Flask, session, redirect, render_template, request, jsonify, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from werkzeug.security import check_password_hash, generate_password_hash

import requests

from helpers import login_required

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database

# database engine object from SQLAlchemy that manages connections to the database
engine = create_engine(os.getenv("DATABASE_URL"))

# create a 'scoped session' that ensures different users' interactions with the
# database are kept separate
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
@login_required
def index():
    """ Show search box """

    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """ Log user in """

    # Forget any user_id
    session.clear()

    username = request.form.get("username")

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return ("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return ("must provide password", 400)

        # Query database for username (http://zetcode.com/db/sqlalchemy/rawsql/)
        # https://docs.sqlalchemy.org/en/latest/core/connections.html#sqlalchemy.engine.ResultProxy
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                            {"username": username})
        
        result = rows.fetchone()

        # Ensure username exists and password is correct
        if result == None or not check_password_hash(result[2], request.form.get("password")):
            return ("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = result[0]
        session["user_name"] = result[1]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """ Log user out """

    # Forget any user ID
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """ Register user """
    
    # Forget any user_id
    session.clear()
    
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return ("must provide username", 400)

        # Query database for username
        userCheck = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username":request.form.get("username")}).fetchone()

        # Check if username already exist
        if userCheck:
            return ("username already exist", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return ("must provide password", 400)

        # Ensure confirmation wass submitted 
        elif not request.form.get("confirmation"):
            return ("must confirm password", 400)

        # Check passwords are equal
        elif not request.form.get("password") == request.form.get("confirmation"):
            return ("passwords didn't match", 400)
        
        # Hash user's password to store in DB
        hashedPassword = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)
        
        # Insert register into DB
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)",
                            {"username":request.form.get("username"), 
                             "password":hashedPassword})

        # Commit changes to database
        db.commit()

        # Redirect user to login page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/search", methods=["GET"])
@login_required
def search():
    """ Get books results """

    # Check book id was provided
    if not request.args.get("book"):
        return render_template("error.html", message="you must provide a book.")

    # Take input and add a wildcard
    query = "%" + request.args.get("book") + "%"

    # Capitalize all words of input for search
    # https://docs.python.org/3.7/library/stdtypes.html?highlight=title#str.title
    query = query.title()
    
    rows = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn LIKE :query OR \
                        title LIKE :query OR \
                        author LIKE :query LIMIT 15",
                        {"query": query})
    
    # Books not founded
    if rows.rowcount == 0:
        return render_template("error.html", message="we can't find books with that id.")
    
    # Fetch all the results
    books = rows.fetchall()

    return render_template("results.html", books=books)

@app.route("/book/<isbn>", methods=['GET','POST'])
@login_required
def book(isbn):
    """ Take the book ISBN and redirect to his page """
    
    if request.method == "POST":
        
        # Fetch form data
        user = session["user_id"]
        rating = request.form.get("rating")
        comment = request.form.get("comment")
        
        # Search book_id by ISBN
        row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})

        # Save id into variable
        book = row.fetchone() # (id,)
        book = book[0]

        # Convert to save into DB
        rating = int(rating)

        print(rating, comment, user, book)

        db.execute("INSERT INTO reviews (user_id, book_id, comment, rating) VALUES \
                    (:user_id, :book_id, :comment, :rating)",
                    {"user_id": user, 
                    "book_id": book, 
                    "comment": comment, 
                    "rating": rating})

        # Commit transactions to DB and close the connection
        db.commit()

        flash('Review submitted!', category='info')

        return redirect("/book/" + isbn)
    
    # GET request
    else:

        row = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn = :isbn",
                        {"isbn": isbn})

        bookInfo = row.fetchall()

        """ GOODREADS reviews """

        # Read API key from env variable
        key = os.getenv("GOODREADS_KEY")
        
        # Query the api with key and ISBN as parameters
        query = requests.get("https://www.goodreads.com/book/review_counts.json",
                params={"key": key, "isbns": isbn})

        # Convert the response to JSON
        response = query.json()

        # "Clean" the JSON before passing it to the bookInfo list
        response = response['books'][0]

        # Append it as the second element on the list. [1]
        bookInfo.append(response)

        """ Users reviews """

        return render_template("book.html", bookInfo=bookInfo)