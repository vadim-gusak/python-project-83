### Hexlet tests and linter status:
[![Actions Status](https://github.com/vadim-gusak/python-project-83/workflows/hexlet-check/badge.svg)](https://github.com/vadim-gusak/python-project-83/actions)
[![my_check](https://github.com/vadim-gusak/python-project-83/actions/workflows/my_workflow_check.yml/badge.svg)](https://github.com/vadim-gusak/python-project-83/actions/workflows/my_workflow_check.yml)
[![Maintainability](https://api.codeclimate.com/v1/badges/ab7444570b4be9d66c91/maintainability)](https://codeclimate.com/github/vadim-gusak/python-project-83/maintainability)

# Анализатор страниц

Небольшое flask приложение для анализа интернет страниц. Делает HTTP GET запрос к странице, выводит 
код ответа и содержимое следующих тэгов:
- h1
- titile
- content из \<meta name="description" content="...">

Введенные адреса сайтов сохраняются в БД на сервере. Результаты проверок также сохраняются.

Схему БД можно посмотреть в файле database.sql

Протестировать работу приложения можно по [ссылке](https://page-analyzer.up.railway.app/)
