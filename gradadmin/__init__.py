from flask import Flask
from flask_login import LoginManager
import cx_Oracle
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
login = LoginManager(app)
login.login_view = 'login'
login.login_message = 'Войдите, чтобы получить доступ к этой странице.'

if app.env == 'production':
    app.config.from_object('config.ProductionConfig')
else:
    app.config.from_object('config.DevelopmentConfig')
    
db_conn = cx_Oracle.connect(app.config['DB_CONN_STRING'])
db_conn.client_identifier = 'gradadmin'
db_conn.clientinfo = 'gradadmin'
db_cursor = db_conn.cursor()

def nvl(val):
    if val is None:
        return ''
    else:
        return val

app.jinja_env.globals.update(nvl=nvl)

from . import views

file_handler = RotatingFileHandler('tmp/GlebAdmin.log', 'a', maxBytes=1 * 1024 * 1024, backupCount=10)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
app.logger.setLevel(logging.INFO)
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.info('GlebAdmin startup')