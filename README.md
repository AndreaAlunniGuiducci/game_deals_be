# Game deals

## Required
- Python 3.8+
- pip
- virtualenv

## Project setup
- Create your env
    - `python -m venv gamesenv`
- Activate your env
    - `gamesenv/Scripts/activate`
- Install required package
    - `pip install -r requirements.txt`
- Configure database
    - `python manage.py makemigrations`
    - `python manage.py migrate`
- Start the server
    - `python manage.py runserver`
