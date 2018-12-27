# Project 1

Web Programming with Python and JavaScript

## :gear: Setup

```bash
# Clone repo
$ git clone https://github.com/marcorichetta/cs50-project1.git

$ cd cs50-project1

# Create a virtualenv (Optional but reccomended)
$ python3 -m venv myvirtualenv -> Nombre del virtualenv

# Activate the virtualenv
$ source myvirtualenv/bin/activate (Linux)

# Install all dependencies
$ pip install -r requirements.txt

# ENV Variables
$ export FLASK_APP = application.py # flask run
$ export DATABASE_URL = Heroku Postgres DB URI
$ export GOODREADS_KEY = Goodreads API Key. # More info: https://www.goodreads.com/api
```