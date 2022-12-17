from flask import Flask, render_template, request, get_flashed_messages, flash
from flask import redirect, url_for
from dotenv import load_dotenv, find_dotenv
import os
from validators.url import url
from urllib.parse import urlparse
import psycopg2
from datetime import datetime
import requests
from bs4 import BeautifulSoup


load_dotenv(find_dotenv())
DATABASE_URL = os.getenv('DATABASE_URL')
SECRET_KEY = os.getenv('SECRET_KEY')
app = Flask(__name__)
app.config.update(SECRET_KEY=SECRET_KEY)


@app.get('/')
def root_get():
    messages = get_flashed_messages(with_categories=True)
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
    errors = list()
    url_from_request = request.form.to_dict().get('url')

    if not url_from_request:
        errors.append('URL обязателен')
    if not url(url_from_request) or len(url_from_request) > 255:
        errors.append('Некорректный URL')

    if errors:
        return render_template(
            'index.html',
            url_from_request=url_from_request,
            errors=errors
        ), 422

    url_id = save_url_and_get_id(url_from_request)
    return redirect(url_for('url_id_get', url_id=url_id))


@app.post('/urls/<url_id>/checks')
def checks_post(url_id):
    insert_new_check(url_id)
    return redirect(url_for('url_id_get', url_id=url_id))


def save_url_and_get_id(url_to_save: str):
    created_at = datetime.now().date()
    parsed_url = urlparse(url_to_save)
    name = f'{parsed_url.scheme}://{parsed_url.netloc}'

    with psycopg2.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT id FROM urls WHERE name = %s LIMIT 1',
                (name,)
            )
            data = cursor.fetchone()
            if data:
                flash('Страница уже существует', 'info')
                return data[0]
            cursor.execute(
                'INSERT INTO urls (name, created_at) '
                'VALUES (%s, %s) RETURNING id',
                (name, created_at)
            )
            url_id = cursor.fetchone()[0]
            flash('Страница успешно добавлена', 'success')

    return url_id


def get_all_urls() -> list:
    urls = list()

    with psycopg2.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM urls ORDER BY id DESC'
            )
            for row in cursor:
                url_id = row[0]
                name = row[1]

                with connection.cursor() as second_cursor:
                    second_cursor.execute(
                        'SELECT status_code, created_at FROM url_checks '
                        'WHERE url_id = %s ORDER BY id LIMIT 1',
                        (url_id,)
                    )
                    data = second_cursor.fetchone()
                    last_status_code = data[0] if data else ''
                    last_check_date = data[1] if data else ''

                urls.append(
                    {
                        'id': url_id,
                        'name': name,
                        'last_status_code': last_status_code,
                        'last_check_date': last_check_date
                    }
                )

    return urls


def get_data_by_id(url_id: int) -> tuple | None:
    with psycopg2.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT name, created_at FROM urls WHERE id = %s',
                (url_id,)
            )
            data = cursor.fetchone()
    return data


def get_all_checks(url_id):
    checks = list()

    with psycopg2.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM url_checks WHERE url_id = %s ORDER BY id DESC',
                (url_id,)
            )
            for row in cursor:
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

    return checks


def insert_new_check(url_id):
    with psycopg2.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT name FROM urls WHERE id = %s LIMIT 1',
                (url_id,)
            )
            name = cursor.fetchone()[0]
            status_code, h1, title, description = \
                get_status_code_h1_title_description(name)
            if status_code is None:
                flash('Произошла ошибка при проверке', 'danger')
                return
            created_at = datetime.now().date()
            cursor.execute(
                'INSERT INTO url_checks '
                '(url_id, status_code, h1, title, description, created_at) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                (
                    url_id,
                    status_code,
                    h1,
                    title,
                    description,
                    created_at
                    )
                )
            flash('Страница успешно проверена', 'success')


def get_status_code_h1_title_description(link: str) -> \
        tuple[None | int, str, str, str]:
    try:
        resp = requests.get(link)
    except requests.exceptions.RequestException as error:
        status_code = error.response.status_code if error.response else None
        return status_code, '', '', ''
    status_code = resp.status_code

    soup = BeautifulSoup(resp.text, 'html.parser')
    h1_tag = soup.find('h1')
    title_tag = soup.find('title')
    description_tag = soup.find('meta', attrs={'name': 'description'})

    h1 = h1_tag.text.strip() if h1_tag else ''
    title = title_tag.text.strip() if title_tag else ''
    description = description_tag['content'].strip() \
        if description_tag else ''

    return status_code, h1, title, description
