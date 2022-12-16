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
    urls = get_all_urls()
    return render_template(
        '/urls/urls.html',
        urls=urls
    )


@app.get('/urls/<url_id>')
def url_id_get(url_id):
    data = get_data_by_id(url_id)
    if not data:
        return 'Page not found!', 404
    name, created_at = data
    messages = get_flashed_messages(with_categories=True)
    checks = get_all_checks(url_id)
    return render_template(
        '/urls/show.html',
        url_id=url_id,
        name=name,
        created_at=created_at,
        messages=messages,
        checks=checks
    )


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


@app.post('/urls/<url_id>/checks')
def checks_post(url_id):
    print(f'{url_id=}')
    insert_new_check(url_id)
    return redirect(url_for('url_id_get', url_id=url_id))


def save_url_and_get_id(url_to_save: str):
    created_at = datetime.now().date()
    parsed_url = urlparse(url_to_save)
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
    with psycopg2.connect(DATABASE_URL) as connection:
        with connection .cursor() as cursor:
            # переписать в один цикл
            cursor.execute(
                'SELECT * FROM urls ORDER BY id DESC'
            )
            rows = cursor.fetchall()
            result = list()
            for row in rows:
                url_id = row[0]
                name = row[1]
                cursor.execute(
                    'SELECT created_at FROM url_checks '
                    'WHERE url_id = %s ORDER BY id LIMIT 1',
                    (url_id,)
                )
                date = cursor.fetchone()
                last_check_date = date[0] if date else ''
                result.append(
                    {
                        'id': url_id,
                        'name': name,
                        'last_check_date': last_check_date
                    }
                )
    return result


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


def get_all_checks(url_id):
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor()
    cursor.execute(
        'SELECT * FROM url_checks WHERE url_id = %s ORDER BY id DESC',
        (url_id,)
    )
    rows = cursor.fetchall()
    checks = list()
    for row in rows:
        checks.append(
            {
                'id': row[0],
                'status_code': row[2],
                'h1': row[3],
                'title': row[4],
                'description': row[5],
                'created_at': row[6]
            }
        )
    connection.commit()
    cursor.close()
    connection.close()
    return checks


def insert_new_check(url_id):
    with psycopg2.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            created_at = datetime.now().date()
            cursor.execute(
                'INSERT INTO url_checks '
                '(url_id, status_code, h1, title, description, created_at) '
                'VALUES'
                '(%s, %s, %s, %s, %s, %s)',
                (
                    url_id,
                    200,
                    'h1 test',
                    'title test',
                    'description test',
                    created_at
                    )
                )
