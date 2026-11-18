import os
from urllib.parse import urlparse, unquote

MOTOR = 'mysql'

MYSQL_HOST = 'localhost'
MYSQL_PUERTO = 3306
MYSQL_USUARIO = 'root'
MYSQL_CONTRASENA = '123'
MYSQL_BASE = 'herdez_scm'

ARCHIVO_SQLITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'herdez_scm.db')

CLAVE_SECRETA = os.environ.get('CLAVE_SECRETA', 'herdez-scm-prototipo-2026')

DIAS_POR_CADUCAR = 30
DIAS_POR_CADUCAR_MP = 5

INTENTOS_MAXIMOS = 5
MINUTOS_BLOQUEO = 15

try:
    from config_local import *
except ImportError:
    pass

if os.environ.get('MYSQL_URL'):
    url = urlparse(os.environ['MYSQL_URL'])
    MYSQL_HOST = url.hostname
    MYSQL_PUERTO = url.port or 3306
    MYSQL_USUARIO = unquote(url.username or '')
    MYSQL_CONTRASENA = unquote(url.password or '')
    MYSQL_BASE = url.path.lstrip('/')
