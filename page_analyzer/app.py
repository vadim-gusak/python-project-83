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


TIMEOUT = 15
GOOD_STATUS_CODE_LIMIT = 299


load_dotenv(find_dotenv())
DATABASE_URL = os.getenv('DATABASE_URL')
SECRET_KEY = os.getenv('SECRET_KEY')
app = Flask(__name__)
app.config.update(SECRET_KEY=SECRET_KEY)


@app.get('/')
def root_get():
    return render_template(
        'index.html',
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
    messages = get_flashed_messages(with_categories=True)
    return render_template(
        '/urls/show.html',
        data=data,
        url_id=url_id,
        messages=messages
    )


@app.post('/urls')
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
                'SELECT DISTINCT ON (urls.id) urls.id, urls.name, '
                'MAX(url_checks.created_at), url_checks.status_code '
                '  FROM urls '
                '  LEFT JOIN url_checks ON urls.id = url_checks.url_id'
                '  GROUP BY '
                '  urls.id, url_checks.status_code, url_checks. created_at'
                '  ORDER BY urls.id DESC, url_checks.created_at DESC;'
            )

            for row in cursor:
                last_status_code = row[3] if row[3] else ''
                last_check_date = row[2] if row[2] else ''
                urls.append(
                    {
                        'id': row[0],
                        'name': row[1],
                        'last_check_date': last_check_date,
                        'last_status_code': last_status_code
                    }
                )

    return urls


def get_data_by_id(url_id: int) -> dict | None:
    data = dict()

    with psycopg2.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                'SELECT name, created_at FROM urls WHERE id = %s',
                (url_id,)
            )
            data_from_urls = cursor.fetchone()
            if not data_from_urls:
                return

            data['name'] = data_from_urls[0]
            data['created_at'] = data_from_urls[1]
            data['checks'] = list()

            cursor.execute(
                'SELECT * FROM url_checks WHERE url_id = %s ORDER BY id DESC',
                (url_id,)
            )

            for row in cursor:
                data['checks'].append(
                    {
                        'id': row[0],
                        'status_code': row[2],
                        'h1': row[3],
                        'title': row[4],
                        'description': row[5],
                        'created_at': row[6]
                    }
                )

    return data


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
        resp = requests.get(link, timeout=TIMEOUT, allow_redirects=False)
        if resp.status_code > GOOD_STATUS_CODE_LIMIT:
            raise requests.exceptions.RequestException
    except requests.exceptions.RequestException:
        return None, '', '', ''

    soup = BeautifulSoup(resp.text, 'html.parser')
    h1_tag = soup.find('h1')
    title_tag = soup.find('title')
    description_tag = soup.find('meta', attrs={'name': 'description'})

    status_code = resp.status_code
    h1 = h1_tag.text.strip() if h1_tag else ''
    title = title_tag.text.strip() if title_tag else ''
    description = description_tag['content'].strip() \
        if description_tag else ''

    return status_code, h1, title, description
