# Prueba rápida: ¿Python sí se conecta a la base herdez_scm?
import config
import db

try:
    conexion = db.conectar_mysql(con_base=True)
    cursor = conexion.cursor()
    cursor.execute('SHOW TABLES')
    tablas = cursor.fetchall()
    conexion.close()
    print('Conexión correcta a la base', config.MYSQL_BASE)
    print('Tablas encontradas:', len(tablas))
except Exception as error:
    print('No se pudo conectar:', error)
    print('Revisa que MySQL esté prendido y la contraseña en config.py')
