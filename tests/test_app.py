from page_analyzer.app import get_status_code_h1_title_description
import pook


@pook.on
def test_get_status_code_h1_title_description():
    pook.get(
        'https://test.ru/',
        reply=200,
        response_body='<html><head><title>title test</title>'
                      '<meta name="description" content="descr"></head>'
                      '<body><h1>H1 test</h1></body></html>'
    )
    status_code, h1, title, description = get_status_code_h1_title_description('https://test.ru/')
    print(f'{status_code=}')
    assert status_code == 200
    assert h1 == 'H1 test'
    assert title == 'title test'
    assert description == 'descr'


@pook.on
def test_get_status_code_h1_title_description_status_code():
    pook.get(
        'https://test.ru/',
        reply=425,
        response_body='<html><head><title>title test</title>'
                      '<meta name="description" content="descr"></head>'
                      '<body><h1>H1 test</h1></body></html>'
    )
    status_code, h1, title, description = get_status_code_h1_title_description('https://test.ru/')
    assert status_code is None
    assert h1 == ''
    assert title == ''
    assert description == ''


# def test_get_status_code_h1_title_description_exception():
#     pook.get(
#         'https://test.ru/',
#         reply=300,
#         response_body='<html><head><title>title test</title>'
#                       '<meta name="description" content="descr"></head>'
#                       '<body><h1>H1 test</h1></body></html>'
#     )
