# jasmin-manage

API for managing project resources on JASMIN.


## Setting up a development environment

`jasmin-manage` requires at least Python 3.8, so you must first ensure a suitable Python version is installed.

First, check out the code:

```sh
git clone https://github.com/cedadev/jasmin-manage.git
cd jasmin-manage
```

Create and activate a new virtual environment and install:

```sh
python -m venv ./venv
source ./venv/bin/activate
pip install -e .
```

Install the local settings:

```sh
cp jasmin_manage_site/settings.py-local jasmin_manage_site/settings.py
```

Apply the migrations (this will create an SQLite database in the same directory as the code):

```sh
python manage.py migrate
```

Create a superuser to access the admin interface:

```sh
python manage.py createsuperuser
```

Then run the development server:

```sh
python manage.py runserver
```

The admin interface will then be available at http://localhost:8000/admin and the API will
be available at http://localhost:8000/api (you must authenticate via the admin).
