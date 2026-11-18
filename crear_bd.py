import os
import sqlite3
import datetime
from werkzeug.security import generate_password_hash
import config

CONTRASENA_DEMO = 'herdez123'

USUARIOS = [
    ('Sandra Torres', 'sandra.torres@herdezscm.mx', 'admin', 'planta', 1),
    ('Yuliana Ferretiz', 'yuliana.ferretiz@herdezscm.mx', 'ventas', 'cdmx', 1),
    ('Jorge Salinas', 'jorge.salinas@herdezscm.mx', 'compras', 'planta', 1),
    ('Perla Toledo', 'perla.toledo@herdezscm.mx', 'produccion', 'planta', 1),
    ('Ana Cristina Infante', 'ana.infante@herdezscm.mx', 'calidad', 'planta', 1),
    ('Daniel Hernández', 'daniel.hernandez@herdezscm.mx', 'almacen', 'planta', 1),
    ('Fernanda Castillo', 'fernanda.castillo@herdezscm.mx', 'logistica', 'planta', 1),
    ('José Antonio Ruiz', 'jose.ruiz@herdezscm.mx', 'gerente', 'planta', 1),
    ('Pedro Ramírez', 'pedro.ramirez@herdezscm.mx', 'ventas', 'cdmx', 0),
]

HOY = datetime.date.today()


def dia(dias):
    return (HOY + datetime.timedelta(days=dias)).strftime('%Y-%m-%d')


def momento(dias, hora):
    return dia(dias) + ' ' + hora


def leer_esquema():
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sql', 'esquema_mysql.sql')
    texto = open(ruta, encoding='utf-8').read()
    lineas = []
    for linea in texto.split('\n'):
        if not linea.strip().startswith('--'):
            lineas.append(linea)
    texto = '\n'.join(lineas)
    sentencias = []
    for parte in texto.split(';'):
        if parte.strip() != '':
            sentencias.append(parte.strip())
    return sentencias


def a_sqlite(sentencia):
    sentencia = sentencia.replace('INT AUTO_INCREMENT PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
    sentencia = sentencia.replace(') ENGINE=InnoDB', ')')
    return sentencia


TABLAS = ['avisos', 'envios', 'rutas', 'solicitudes_reabastecimiento', 'inspecciones_calidad',
          'consumos_produccion', 'movimientos_almacen', 'lotes', 'ordenes_produccion', 'detalle_pedido',
          'pedidos', 'recetas', 'clientes', 'proveedores', 'articulos', 'bitacora', 'usuarios', 'sedes',
          'roles_permisos']


def crear_mysql():
    import pymysql
    conexion = pymysql.connect(host=config.MYSQL_HOST, port=config.MYSQL_PUERTO, user=config.MYSQL_USUARIO,
                               password=config.MYSQL_CONTRASENA, charset='utf8mb4')
    cursor = conexion.cursor()
    cursor.execute('CREATE DATABASE IF NOT EXISTS ' + config.MYSQL_BASE + ' CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    cursor.execute('USE ' + config.MYSQL_BASE)
    cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
    for tabla in TABLAS:
        cursor.execute('DROP TABLE IF EXISTS ' + tabla)
    cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
    for sentencia in leer_esquema():
        cursor.execute(sentencia)
    conexion.commit()
    return conexion


def crear_sqlite():
    conexion = sqlite3.connect(config.ARCHIVO_SQLITE)
    conexion.execute('PRAGMA foreign_keys = OFF')
    for tabla in TABLAS:
        conexion.execute('DROP TABLE IF EXISTS ' + tabla)
    conexion.execute('PRAGMA foreign_keys = ON')
    for sentencia in leer_esquema():
        conexion.execute(a_sqlite(sentencia))
    conexion.commit()
    return conexion


def insertar(conexion, tabla, datos):
    columnas = list(datos.keys())
    marcas = []
    for c in columnas:
        marcas.append('%s')
    sql = 'INSERT INTO ' + tabla + ' (' + ', '.join(columnas) + ') VALUES (' + ', '.join(marcas) + ')'
    if config.MOTOR == 'sqlite':
        sql = sql.replace('%s', '?')
    cursor = conexion.cursor()
    valores = []
    for c in columnas:
        valores.append(datos[c])
    cursor.execute(sql, valores)
    return cursor.lastrowid


def llenar(conexion):
    permisos = {
        'ventas': {'pedidos': (1, 1)},
        'compras': {'inventarios': (1, 1)},
        'produccion': {'produccion': (1, 1), 'inventarios': (1, 0)},
        'calidad': {'calidad': (1, 1), 'logistica': (1, 0)},
        'almacen': {'almacen': (1, 1), 'inventarios': (1, 1)},
        'logistica': {'logistica': (1, 1)},
        'gerente': {'reportes': (1, 1), 'pedidos': (1, 0), 'inventarios': (1, 0)},
        'admin': {'usuarios': (1, 1)},
    }
    modulos = ['pedidos', 'inventarios', 'produccion', 'calidad', 'almacen', 'logistica', 'reportes', 'usuarios']
    for rol in permisos:
        for modulo in modulos:
            valor = permisos[rol].get(modulo, (0, 0))
            insertar(conexion, 'roles_permisos', {'rol': rol, 'modulo': modulo,
                                                  'puede_consultar': valor[0], 'puede_registrar': valor[1]})

    planta = insertar(conexion, 'sedes', {'nombre': 'Planta San Luis Potosí', 'tipo': 'Planta', 'direccion': 'Zona Industrial, San Luis Potosí, S.L.P.'})
    cedis_cdmx = insertar(conexion, 'sedes', {'nombre': 'CEDIS Ciudad de México', 'tipo': 'Centro de distribución', 'direccion': 'Iztapalapa, Ciudad de México'})
    insertar(conexion, 'sedes', {'nombre': 'CEDIS Monterrey', 'tipo': 'Centro de distribución', 'direccion': 'Apodaca, Nuevo León'})
    insertar(conexion, 'sedes', {'nombre': 'CEDIS Guadalajara', 'tipo': 'Centro de distribución', 'direccion': 'Zapopan, Jalisco'})

    clave = generate_password_hash(CONTRASENA_DEMO, method='pbkdf2:sha256')
    sede = {'planta': planta, 'cdmx': cedis_cdmx}
    u = {}
    for persona in USUARIOS:
        u[persona[2] if persona[4] == 1 else 'ventas2'] = insertar(conexion, 'usuarios', {
            'nombre': persona[0], 'correo': persona[1], 'contrasena': clave, 'rol': persona[2],
            'sede_id': sede[persona[3]], 'activo': persona[4], 'intentos_fallidos': 0})

    art = {}
    articulos = [
        ('PT-001', 'Rajas de jalapeño 380 g', 'Producto terminado', 'cajas', 730, 100),
        ('PT-002', 'Chiles chipotles adobados 105 g', 'Producto terminado', 'cajas', 730, 80),
        ('PT-003', 'Puré de tomate 210 g', 'Producto terminado', 'cajas', 540, 120),
        ('PT-004', 'Chiles jalapeños en escabeche 220 g', 'Producto terminado', 'cajas', 730, 100),
        ('MP-001', 'Chile jalapeño', 'Materia prima', 'kg', 20, 800),
        ('MP-002', 'Chile chipotle seco', 'Materia prima', 'kg', 240, 200),
        ('MP-003', 'Jitomate', 'Materia prima', 'kg', 15, 1500),
        ('MP-004', 'Cebolla blanca', 'Materia prima', 'kg', 60, 200),
        ('MP-005', 'Vinagre blanco', 'Materia prima', 'L', 365, 400),
        ('ME-001', 'Lata 380 g', 'Material de empaque', 'piezas', 1800, 3000),
        ('ME-002', 'Lata 210-220 g', 'Material de empaque', 'piezas', 1800, 3000),
        ('ME-003', 'Lata 105 g', 'Material de empaque', 'piezas', 1800, 2000),
        ('ME-004', 'Tapa abre fácil', 'Material de empaque', 'piezas', 1800, 6000),
        ('ME-005', 'Etiqueta impresa', 'Material de empaque', 'piezas', 1800, 6000),
        ('ME-006', 'Caja de cartón 24 piezas', 'Material de empaque', 'piezas', 1800, 300),
    ]
    for a in articulos:
        art[a[0]] = insertar(conexion, 'articulos', {'codigo': a[0], 'nombre': a[1], 'tipo': a[2], 'unidad': a[3],
                                                     'vida_util_dias': a[4], 'nivel_minimo': a[5]})

    recetas = {
        'PT-001': [('MP-001', 6.5), ('MP-004', 1.0), ('MP-005', 2.0), ('ME-001', 24), ('ME-004', 24), ('ME-005', 24), ('ME-006', 1)],
        'PT-002': [('MP-002', 2.0), ('MP-003', 0.8), ('MP-005', 0.5), ('ME-003', 24), ('ME-004', 24), ('ME-005', 24), ('ME-006', 1)],
        'PT-003': [('MP-003', 5.5), ('ME-002', 24), ('ME-004', 24), ('ME-005', 24), ('ME-006', 1)],
        'PT-004': [('MP-001', 4.0), ('MP-004', 0.5), ('MP-005', 1.2), ('ME-002', 24), ('ME-004', 24), ('ME-005', 24), ('ME-006', 1)],
    }
    for producto in recetas:
        for material in recetas[producto]:
            insertar(conexion, 'recetas', {'producto_id': art[producto], 'material_id': art[material[0]],
                                           'cantidad_por_caja': material[1]})

    prov = {}
    prov['chiles'] = insertar(conexion, 'proveedores', {'nombre': 'Agrícola del Valle', 'contacto': 'Ing. Ramón Ortiz', 'telefono': '487 872 1100', 'materiales': 'Chile jalapeño, chile chipotle'})
    prov['hortalizas'] = insertar(conexion, 'proveedores', {'nombre': 'Hortalizas del Bajío', 'contacto': 'Lic. Teresa Ruiz', 'telefono': '461 615 2200', 'materiales': 'Jitomate, cebolla'})
    prov['latas'] = insertar(conexion, 'proveedores', {'nombre': 'Envases Metálicos del Centro', 'contacto': 'Ing. Óscar Leal', 'telefono': '444 812 3300', 'materiales': 'Latas y tapas'})
    prov['etiquetas'] = insertar(conexion, 'proveedores', {'nombre': 'Etiquetas y Cartón Potosí', 'contacto': 'Lic. Diana Soto', 'telefono': '444 815 4400', 'materiales': 'Etiquetas y cajas de cartón'})
    prov['vinagre'] = insertar(conexion, 'proveedores', {'nombre': 'Vinagres Potosinos', 'contacto': 'Sr. Hugo Lara', 'telefono': '444 818 5500', 'materiales': 'Vinagre blanco'})

    cli = []
    cli.append(insertar(conexion, 'clientes', {'nombre': 'Supermercados del Centro', 'tipo': 'Autoservicio', 'direccion': 'Querétaro, Qro.', 'contacto': 'Compras regionales'}))
    cli.append(insertar(conexion, 'clientes', {'nombre': 'Abarrotes La Esperanza', 'tipo': 'Mayorista', 'direccion': 'Rioverde, S.L.P.', 'contacto': 'Sr. Tomás Galván'}))
    cli.append(insertar(conexion, 'clientes', {'nombre': 'Distribuidora del Norte', 'tipo': 'Distribuidor', 'direccion': 'Monterrey, N.L.', 'contacto': 'Lic. Paola Garza'}))
    cli.append(insertar(conexion, 'clientes', {'nombre': 'Tiendas Occidente', 'tipo': 'Autoservicio', 'direccion': 'Guadalajara, Jal.', 'contacto': 'Compras nacionales'}))

    ruta = {}
    ruta['centro'] = insertar(conexion, 'rutas', {'nombre': 'Ruta Centro', 'sede_origen_id': planta, 'destinos': 'Querétaro, Ciudad de México'})
    ruta['huasteca'] = insertar(conexion, 'rutas', {'nombre': 'Ruta Huasteca', 'sede_origen_id': planta, 'destinos': 'Rioverde, Ciudad Valles'})
    ruta['norte'] = insertar(conexion, 'rutas', {'nombre': 'Ruta Norte', 'sede_origen_id': planta, 'destinos': 'Monterrey, Saltillo'})
    ruta['occidente'] = insertar(conexion, 'rutas', {'nombre': 'Ruta Occidente', 'sede_origen_id': planta, 'destinos': 'Guadalajara, Aguascalientes'})

    def orden(producto, planeada, producida, dias_prog, dias_fin, estado, pedido=None):
        return insertar(conexion, 'ordenes_produccion', {
            'articulo_id': art[producto], 'cantidad_planeada': planeada, 'cantidad_producida': producida,
            'pedido_id': pedido, 'fecha_programada': dia(dias_prog), 'fecha_termino': dia(dias_fin) if dias_fin is not None else None,
            'estado': estado, 'usuario_id': u['produccion']})

    o1 = orden('PT-001', 140, 140, -62, -60, 'Terminada')
    o2 = orden('PT-001', 160, 160, -30, -28, 'Terminada')
    o3 = orden('PT-002', 90, 90, -48, -46, 'Terminada')
    o4 = orden('PT-003', 460, 460, -40, -38, 'Terminada')
    o5 = orden('PT-004', 330, 330, -36, -35, 'Terminada')
    o6 = orden('PT-001', 100, 100, -24, -22, 'Terminada')
    o7 = orden('PT-003', 90, 90, -13, -12, 'Terminada')
    o8 = orden('PT-004', 100, 100, -2, -1, 'Terminada')
    orden('PT-002', 100, 0, 1, None, 'Programada')

    lote = {}

    def nuevo_lote(clave, numero, codigo, sede, ubicacion, cantidad, dias_entrada, dias_caducidad, estado, proveedor=None, orden_id=None, cantidad_original=None):
        lote[clave] = insertar(conexion, 'lotes', {
            'numero_lote': numero, 'articulo_id': art[codigo], 'sede_id': sede, 'ubicacion': ubicacion,
            'cantidad': cantidad, 'fecha_entrada': dia(dias_entrada), 'fecha_caducidad': dia(dias_caducidad),
            'estado_calidad': estado, 'proveedor_id': proveedor, 'orden_id': orden_id})
        if cantidad_original is None:
            cantidad_original = cantidad
        if cantidad_original > 0:
            insertar(conexion, 'movimientos_almacen', {'tipo': 'Entrada', 'lote_id': lote[clave], 'cantidad': cantidad_original,
                                                       'fecha': dia(dias_entrada), 'usuario_id': u['almacen'], 'pedido_id': None})

    nuevo_lote('rajas_viejo', 'L' + dia(-60).replace('-', '')[2:] + '-01', 'PT-001', planta, 'A-01-02', 40, -60, 18, 'Liberado', None, o1, 140)
    nuevo_lote('rajas_nuevo', 'L' + dia(-28).replace('-', '')[2:] + '-01', 'PT-001', planta, 'A-01-03', 130, -28, 702, 'Liberado', None, o2, 160)
    nuevo_lote('rajas_mal', 'L' + dia(-22).replace('-', '')[2:] + '-03', 'PT-001', planta, 'Cuarentena', 0, -22, 708, 'Rechazado', None, o6, 0)
    nuevo_lote('chipotles', 'L' + dia(-46).replace('-', '')[2:] + '-02', 'PT-002', planta, 'B-02-01', 60, -46, 684, 'Liberado', None, o3, 90)
    nuevo_lote('pure', 'L' + dia(-38).replace('-', '')[2:] + '-05', 'PT-003', planta, 'C-01-01', 260, -38, 502, 'Liberado', None, o4, 460)
    nuevo_lote('pure_ret', 'L' + dia(-12).replace('-', '')[2:] + '-02', 'PT-003', planta, 'Cuarentena', 90, -12, 528, 'Retenido', None, o7)
    nuevo_lote('jalapenos', 'L' + dia(-35).replace('-', '')[2:] + '-04', 'PT-004', planta, 'A-03-01', 150, -35, 695, 'Liberado', None, o5, 330)
    nuevo_lote('jalapenos_pend', 'L' + dia(-1).replace('-', '')[2:] + '-01', 'PT-004', planta, 'Por asignar', 100, -1, 729, 'Pendiente', None, o8, 0)

    nuevo_lote('mp_jal1', 'MP-' + dia(-8).replace('-', '')[2:] + '-11', 'MP-001', planta, 'R-01', 1200, -8, 12, 'Liberado', prov['chiles'])
    nuevo_lote('mp_jal2', 'MP-' + dia(-2).replace('-', '')[2:] + '-12', 'MP-001', planta, 'R-02', 1500, -2, 18, 'Liberado', prov['chiles'])
    nuevo_lote('mp_chip', 'MP-' + dia(-30).replace('-', '')[2:] + '-21', 'MP-002', planta, 'S-01', 150, -30, 210, 'Liberado', prov['chiles'])
    nuevo_lote('mp_jit1', 'MP-' + dia(-4).replace('-', '')[2:] + '-31', 'MP-003', planta, 'R-03', 2400, -4, 4, 'Liberado', prov['hortalizas'])
    nuevo_lote('mp_jit2', 'MP-' + dia(-1).replace('-', '')[2:] + '-32', 'MP-003', planta, 'R-04', 1800, -1, 14, 'Liberado', prov['hortalizas'])
    nuevo_lote('mp_ceb', 'MP-' + dia(-10).replace('-', '')[2:] + '-41', 'MP-004', planta, 'S-02', 600, -10, 50, 'Liberado', prov['hortalizas'])
    nuevo_lote('mp_vin', 'MP-' + dia(-25).replace('-', '')[2:] + '-51', 'MP-005', planta, 'S-03', 900, -25, 340, 'Liberado', prov['vinagre'])
    nuevo_lote('me_lg', 'ME-' + dia(-40).replace('-', '')[2:] + '-61', 'ME-001', planta, 'E-01', 6000, -40, 1760, 'Liberado', prov['latas'])
    nuevo_lote('me_lm', 'ME-' + dia(-40).replace('-', '')[2:] + '-62', 'ME-002', planta, 'E-02', 9000, -40, 1760, 'Liberado', prov['latas'])
    nuevo_lote('me_lc', 'ME-' + dia(-40).replace('-', '')[2:] + '-63', 'ME-003', planta, 'E-03', 1500, -40, 1760, 'Liberado', prov['latas'])
    nuevo_lote('me_tap', 'ME-' + dia(-40).replace('-', '')[2:] + '-64', 'ME-004', planta, 'E-04', 20000, -40, 1760, 'Liberado', prov['latas'])
    nuevo_lote('me_eti', 'ME-' + dia(-20).replace('-', '')[2:] + '-71', 'ME-005', planta, 'E-05', 18000, -20, 1780, 'Liberado', prov['etiquetas'])
    nuevo_lote('me_caj', 'ME-' + dia(-20).replace('-', '')[2:] + '-72', 'ME-006', planta, 'E-06', 900, -20, 1780, 'Liberado', prov['etiquetas'])

    inspecciones = [
        ('rajas_viejo', 'Liberado', 'Vacío y sellado correctos', -60),
        ('chipotles', 'Liberado', 'Sin observaciones', -46),
        ('pure', 'Liberado', 'Sin observaciones', -38),
        ('jalapenos', 'Liberado', 'Sin observaciones', -35),
        ('rajas_nuevo', 'Liberado', 'Sin observaciones', -28),
        ('rajas_mal', 'Rechazado', 'Sellado defectuoso en muestra', -22),
        ('pure_ret', 'Retenido', 'Vacío insuficiente en algunas latas; se repite prueba', -12),
    ]
    for i in inspecciones:
        insertar(conexion, 'inspecciones_calidad', {'lote_id': lote[i[0]], 'resultado': i[1], 'observaciones': i[2],
                                                    'fecha': dia(i[3]), 'usuario_id': u['calidad']})

    def pedido(cliente, dias_reg, dias_req, estado, lineas):
        p = insertar(conexion, 'pedidos', {'cliente_id': cliente, 'fecha_registro': dia(dias_reg), 'fecha_requerida': dia(dias_req),
                                           'estado': estado, 'usuario_id': u['ventas']})
        for linea in lineas:
            insertar(conexion, 'detalle_pedido', {'pedido_id': p, 'articulo_id': art[linea[0]], 'cantidad': linea[1]})
        return p

    def salida(clave_lote, cantidad, dias, pedido_id):
        insertar(conexion, 'movimientos_almacen', {'tipo': 'Salida', 'lote_id': lote[clave_lote], 'cantidad': cantidad,
                                                   'fecha': dia(dias), 'usuario_id': u['almacen'], 'pedido_id': pedido_id})

    def envio(pedido_id, clave_ruta, destino, dias_salida, dias_entrega, estado):
        insertar(conexion, 'envios', {'pedido_id': pedido_id, 'ruta_id': ruta[clave_ruta], 'destino': destino,
                                      'fecha_salida': dia(dias_salida), 'fecha_entrega': dia(dias_entrega) if dias_entrega is not None else None,
                                      'estado': estado})

    p1 = pedido(cli[0], -40, -35, 'Entregado', [('PT-001', 60), ('PT-003', 120)])
    salida('rajas_viejo', 60, -37, p1)
    salida('pure', 120, -37, p1)
    envio(p1, 'centro', 'Querétaro, Qro.', -37, -36, 'Entregado')

    p2 = pedido(cli[2], -30, -24, 'Entregado', [('PT-004', 150)])
    salida('jalapenos', 150, -26, p2)
    envio(p2, 'norte', 'Monterrey, N.L.', -26, -23, 'Entregado')

    p3 = pedido(cli[1], -20, -15, 'Entregado', [('PT-001', 40), ('PT-002', 30)])
    salida('rajas_viejo', 40, -17, p3)
    salida('chipotles', 30, -17, p3)
    envio(p3, 'huasteca', 'Rioverde, S.L.P.', -17, -16, 'Entregado')

    p4 = pedido(cli[3], -12, -6, 'Entregado', [('PT-003', 80)])
    salida('pure', 80, -9, p4)
    envio(p4, 'occidente', 'Guadalajara, Jal.', -9, -7, 'Entregado')

    p5 = pedido(cli[0], -5, 2, 'Enviado', [('PT-001', 30)])
    salida('rajas_nuevo', 30, -2, p5)
    envio(p5, 'centro', 'Ciudad de México', -1, None, 'En tránsito')

    p6 = pedido(cli[2], -3, 4, 'Surtido', [('PT-004', 30)])
    salida('jalapenos', 30, -1, p6)

    p7 = pedido(cli[1], -1, 6, 'Registrado', [('PT-003', 40), ('PT-002', 20)])

    insertar(conexion, 'solicitudes_reabastecimiento', {'articulo_id': art['ME-003'], 'cantidad': 3000, 'fecha': dia(-2),
                                                        'estado': 'Pendiente', 'usuario_id': u['compras']})
    eventos = [
        (u['ventas'], 'Registró el pedido PED-' + str(p7).zfill(4), 'pedidos', momento(-1, '10:15:00')),
        (u['produccion'], 'Registró producción de la orden OP-' + str(o8).zfill(4), 'ordenes_produccion', momento(-1, '17:40:00')),
        (u['compras'], 'Solicitó reabastecimiento de Lata 105 g', 'solicitudes_reabastecimiento', momento(-2, '09:05:00')),
        (u['calidad'], 'Retuvo un lote de puré de tomate', 'inspecciones_calidad', momento(-12, '12:30:00')),
    ]
    for e in eventos:
        insertar(conexion, 'bitacora', {'usuario_id': e[0], 'operacion': e[1], 'tabla_afectada': e[2], 'fecha_hora': e[3]})

    conexion.commit()


def principal():
    print('Creando la base de datos del prototipo Herdez SCM...')
    conexion = None
    if config.MOTOR == 'mysql':
        try:
            conexion = crear_mysql()
            print('  Motor: MySQL (' + config.MYSQL_HOST + ', base ' + config.MYSQL_BASE + ')')
        except Exception as error:
            print('  No se pudo conectar a MySQL:', error)
            print('  Se usará SQLite en el archivo', config.ARCHIVO_SQLITE)
            config.MOTOR = 'sqlite'
    if conexion is None:
        conexion = crear_sqlite()
        print('  Motor: SQLite (' + config.ARCHIVO_SQLITE + ')')
    llenar(conexion)
    conexion.close()
    print('Listo. Usuarios (contraseña: ' + CONTRASENA_DEMO + '):')
    for persona in USUARIOS:
        if persona[4]:
            print('   ' + persona[1] + '  (' + persona[2] + ')')

if __name__ == '__main__':
    principal()
