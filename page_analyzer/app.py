from flask import Flask

app = Flask(__name__)


@app.get('/')
def root_get():
    return 'Hello, world!'
