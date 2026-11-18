import sqlite3
import datetime
import decimal
from flask import g
import config


def conectar_mysql(con_base=True):
    import pymysql
    datos = {
        'host': config.MYSQL_HOST,
        'port': config.MYSQL_PUERTO,
        'user': config.MYSQL_USUARIO,
        'password': config.MYSQL_CONTRASENA,
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': False,
    }
    if con_base:
        datos['database'] = config.MYSQL_BASE
    return pymysql.connect(**datos)


def conectar_sqlite():
    conexion = sqlite3.connect(config.ARCHIVO_SQLITE)
    conexion.row_factory = sqlite3.Row
    conexion.execute('PRAGMA foreign_keys = ON')
    return conexion


def nueva_conexion():
    if config.MOTOR == 'mysql':
        return conectar_mysql()
    return conectar_sqlite()


def probar_mysql():
    try:
        conexion = conectar_mysql()
        conexion.close()
        return True
    except Exception as error:
        print('  MySQL no respondió:', error)
        return False


def obtener_conexion():
    if 'conexion' not in g:
        g.conexion = nueva_conexion()
    return g.conexion


def cerrar_conexion(error=None):
    conexion = g.pop('conexion', None)
    if conexion is None:
        return
    if error is None:
        conexion.commit()
    else:
        conexion.rollback()
    conexion.close()


def preparar(sql):
    if config.MOTOR == 'sqlite':
        return sql.replace('%s', '?')
    return sql


def limpiar_valor(valor):
    if isinstance(valor, datetime.datetime):
        return valor.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(valor, datetime.date):
        return valor.strftime('%Y-%m-%d')
    if isinstance(valor, decimal.Decimal):
        return float(valor)
    return valor


def limpiar_fila(fila):
    resultado = {}
    for llave in fila.keys():
        resultado[llave] = limpiar_valor(fila[llave])
    return resultado


def consultar(sql, parametros=()):
    cursor = obtener_conexion().cursor()
    cursor.execute(preparar(sql), parametros)
    filas = cursor.fetchall()
    cursor.close()
    lista = []
    for fila in filas:
        lista.append(limpiar_fila(fila))
    return lista


def consultar_uno(sql, parametros=()):
    filas = consultar(sql, parametros)
    if len(filas) == 0:
        return None
    return filas[0]


def ejecutar(sql, parametros=()):
    cursor = obtener_conexion().cursor()
    cursor.execute(preparar(sql), parametros)
    nuevo_id = cursor.lastrowid
    cursor.close()
    return nuevo_id


def hoy():
    return datetime.date.today().strftime('%Y-%m-%d')


def ahora():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def sumar_dias(fecha_texto, dias):
    fecha = datetime.datetime.strptime(fecha_texto[:10], '%Y-%m-%d').date()
    return (fecha + datetime.timedelta(days=dias)).strftime('%Y-%m-%d')


def dias_entre(fecha_inicio, fecha_fin):
    inicio = datetime.datetime.strptime(fecha_inicio[:10], '%Y-%m-%d').date()
    fin = datetime.datetime.strptime(fecha_fin[:10], '%Y-%m-%d').date()
    return (fin - inicio).days
