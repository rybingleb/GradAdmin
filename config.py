class Config(object):
    CSRF_ENABLED = True
    SECRET_KEY = 'da1s465456S4S58VFRH54dE54g8f74G5G46s'

class ProductionConfig(Config):
    DB_CONN_STRING = 'infonext/k711HT150@172.31.0.19/infoline'

class DevelopmentConfig(Config):
    DEBUG = True
    DB_CONN_STRING = 'infonext/infonext@10.0.2.156/daytest'
    