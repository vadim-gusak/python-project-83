from flask import Flask, render_template, request, get_flashed_messages, flash
from flask import redirect, url_for
from dotenv import load_dotenv, find_dotenv
import os
from validators.url import url
from urllib.parse import urlparse
import psycopg2
from datetime import datetime


load_dotenv(find_dotenv())
DATABASE_URL = os.getenv('DATABASE_URL')
SECRET_KEY = os.getenv('SECRET_KEY')
app = Flask(__name__)
app.config.update(SECRET_KEY=SECRET_KEY)


@app.get('/')
def root_get():
    messages = get_flashed_messages()
    return render_template(
        'index.html',
        messages=messages,
        url_from_request=''
    )


@app.get('/urls')
def urls_get():
    rows = get_all_urls()
    return render_template('/urls/urls.html', rows=rows)


@app.get('/urls/<url_id>')
def url_id_get(url_id):
    data = get_data_by_id(url_id)
    if not data:
        return 'Page not found!', 404
    name, created_at = data
    messages = get_flashed_messages(with_categories=True)
    return render_template('/urls/show.html', url_id=url_id,
                           name=name, created_at=created_at,
                           messages=messages)


@app.post('/')
def root_post():
    errors, messages = False, list()
    url_from_request = request.form.to_dict().get('url')
    if not url_from_request:
        messages.append('URL обязателен')
        errors = True
    elif not url(url_from_request):
        messages.append('Некорректный URL')
        errors = True
    if errors:
        return render_template('index.html',
                               messages=messages,
                               url_from_request=url_from_request), 422
    url_id = save_url_and_get_id(url_from_request)
    return redirect(url_for('url_id_get', url_id=url_id))


def save_url_and_get_id(url_to_save: str):
    created_at = datetime.now().date()
    parsed_url = urlparse((url_to_save))
    name = f'{parsed_url.scheme}://{parsed_url.netloc}'
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor()
    cursor.execute('SELECT id FROM urls WHERE name = %s LIMIT 1', (name,))
    data = cursor.fetchone()
    if data:
        url_id = data[0]
        flash('Страница уже существует', 'info')
    else:
        cursor.execute('INSERT INTO urls (name, created_at)'
                       ' VALUES (%s, %s) RETURNING id',
                       (name, created_at))
        url_id = cursor.fetchone()[0]
        flash('Страница успешно добавлена', 'success')
    connection.commit()
    cursor.close()
    connection.close()
    return url_id


def get_all_urls() -> list:
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM urls ORDER BY id DESC')
    rows = cursor.fetchall()
    connection.commit()
    cursor.close()
    connection.close()
    return rows


def get_data_by_id(url_id: int) -> tuple | None:
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor()
    cursor.execute(
        'SELECT name, created_at FROM urls WHERE id = %s',
        (url_id,)
    )
    data = cursor.fetchone()
    connection.commit()
    cursor.close()
    connection.close()
    return data
