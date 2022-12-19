import pook
from page_analyzer.app import save_url_and_get_id, get_all_urls
from page_analyzer.app import insert_new_check
import os
from datetime import datetime
from page_analyzer import app
import psycopg2
import pytest


app.config.update(
    {
        'TESTING': True
    }
)

# db_schema_path = os.path.join(
#     os.path.join(os.getcwd(), 'tests'), 'test_database.sql'
# )

with open('./tests/test_database.sql') as file:
    schema = file.read()

date = datetime.now().date()


@pytest.fixture
def db(postgresql):
    connection = f'postgresql://{postgresql.info.user}:' \
                 f'@{postgresql.info.host}:{postgresql.info.port}/' \
                 f'{postgresql.info.dbname}'
    db = psycopg2.connect(connection)
    with db:
        with db.cursor() as cursor:
            cursor.execute(schema)
            cursor.execute(
                'INSERT INTO urls (name, created_at) '
                'VALUES (%s, %s), (%s, %s)',
                ('https://test.ru', date, 'https://www.psycopg.org', date)
            )
            cursor.execute(
                'INSERT INTO url_checks '
                '(url_id, status_code, h1, title, description, created_at) '
                'VALUES (%s, %s, %s, %s, %s, %s), (%s, %s, %s, %s, %s, %s)',
                (1, 200, "", "", "", date, 2, 201, "", "", "", date)
            )
    return db


def test_save_url_and_get_id(db):
    url_for_save = 'https://test-test.ru/?test=123'
    expected_name = 'https://test-test.ru'
    expected_id = 3
    with app.test_request_context():
        test_id = save_url_and_get_id(url_for_save, db_connect=db)
        test_id_second = save_url_and_get_id(url_for_save, db_connect=db)

    with db:
        with db.cursor() as cursor:
            cursor.execute(
                'SELECT name, created_at FROM urls ORDER BY id DESC LIMIT 1'
            )
            data = cursor.fetchone()
            name_from_db = data[0]
            date_from_db = data[1]

    assert test_id == expected_id
    assert test_id_second == expected_id
    assert name_from_db == expected_name
    assert date_from_db == date


def test_get_all_urls(db):
    all_urls = [
        {
            'id': 2,
            'name': 'https://www.psycopg.org',
            'last_status_code': 201,
            'last_check_date': date
        },
        {
            'id': 1,
            'name': 'https://test.ru',
            'last_status_code': 200,
            'last_check_date': date
        }
    ]

    test_urls = get_all_urls(db_connect=db)
    assert test_urls == all_urls


@pook.on
def test_insert_new_check(db):
    url_for_test_1 = 'https://www.psycopg.org'
    id_for_insert_1 = 2
    url_for_test_2 = 'https://test.ru'
    id_for_insert_2 = 1

    pook.get(
        url_for_test_1,
        reply=200,
        response_body='''<html><head><title>Test title</title>
        <meta name="description" content="Test description"></head>
        <body><h1>Test H1</h1></body></html>'''
    )

    with app.test_request_context():
        insert_new_check(id_for_insert_1, db_connect=db)

    pook.get(
        url_for_test_2,
        reply=500,
        response_body='''<html><head><title>Second title</title>
        <meta name="description" content="New description"></head>
        <body><h1>Wow H1</h1></body></html>'''
    )

    with app.test_request_context():
        insert_new_check(id_for_insert_2, db_connect=db)

    with db:
        with db.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM url_checks ORDER BY id DESC LIMIT 1'
            )
            data = cursor.fetchone()
            id_, url_id, status_code, h1 = data[0], data[1], data[2], data[3]
            title, description, created_at = data[4], data[5], data[6]

    assert id_ == 3
    assert url_id == id_for_insert_1
    assert status_code == 200
    assert h1 == 'Test H1'
    assert title == 'Test title'
    assert description == 'Test description'
    assert created_at == date
