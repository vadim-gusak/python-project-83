from page_analyzer.app import save_url_and_get_id, get_all_urls
import os
from datetime import datetime
from page_analyzer import app
import psycopg2
import pytest
from pytest_postgresql import factories


app.config.update(
    {
        'TESTING': True
    }
)
postgresql_my = factories.postgresql('postgresql_my_proc')
db_schema_path = os.path.join(
    os.path.join(os.getcwd(), 'tests'), 'test_database.sql'
)
with open(db_schema_path) as file:
    schema = file.read()

date = datetime.now().date()
URL_FOR_SAVE = 'https://test.ru/?test=123'
EXPECTED_NAME = 'https://test.ru'
EXPECTED_ID = 1
ALL_URLS = [
    {
        'id': 2,
        'name': 'https://www.psycopg.org',
        'last_status_code': 200,
        'last_check_date': date
    },
    {
        'id': 1,
        'name': 'https://test.ru',
        'last_status_code': 200,
        'last_check_date': date
    }
]


@pytest.fixture
def db(postgresql):
    connection = f'postgresql://{postgresql.info.user}:' \
                 f'@{postgresql.info.host}:{postgresql.info.port}/' \
                 f'{postgresql.info.dbname}'
    db = psycopg2.connect(connection)
    with db:
        with db.cursor() as cursor:
            cursor.execute(schema)
    return db


def test_save_url_and_get_id_2(db):
    with app.test_request_context():
        test_id = save_url_and_get_id(URL_FOR_SAVE, db_connect=db)
        test_id_second = save_url_and_get_id(URL_FOR_SAVE, db_connect=db)

    with db:
        with db.cursor() as cursor:
            cursor.execute('SELECT name, created_at FROM urls')
            data = cursor.fetchone()
            name_from_db = data[0]
            date_from_db = data[1]

    assert test_id == EXPECTED_ID
    assert test_id_second == EXPECTED_ID
    assert name_from_db == EXPECTED_NAME
    assert date_from_db == date


def test_get_all_urls(db):
    with app.test_request_context():
        save_url_and_get_id(URL_FOR_SAVE, db_connect=db)
        save_url_and_get_id('https://www.psycopg.org', db_connect=db)

    with db:
        with db.cursor() as cursor:
            cursor.execute(
                'INSERT INTO url_checks '
                '(url_id, status_code, h1, title, description, created_at) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                (1, 200, "", "", "", date)
            )
            cursor.execute(
                'INSERT INTO url_checks '
                '(url_id, status_code, h1, title, description, created_at) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                (2, 200, "", "", "", date)
            )

    test_urls = get_all_urls(db_connect=db)
    assert test_urls == ALL_URLS
