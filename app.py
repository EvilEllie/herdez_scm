import datetime
import importlib
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
import config
import db
import logica
import seguridad

app = Flask(__name__)
app.secret_key = config.CLAVE_SECRETA

MODULOS_DEL_SISTEMA = ['pedidos', 'inventarios', 'produccion', 'calidad', 'almacen', 'logistica', 'reportes', 'usuarios']
for nombre_modulo in MODULOS_DEL_SISTEMA:
    try:
        modulo = importlib.import_module('modulos.' + nombre_modulo)
    except ModuleNotFoundError:
        continue
    app.register_blueprint(modulo.bp)


def enlace(endpoint, **datos):
    if '.' in endpoint and endpoint.split('.')[0] not in app.blueprints:
        return None
    return url_for(endpoint, **datos)


app.teardown_appcontext(db.cerrar_conexion)


@app.template_filter('numero')
def filtro_numero(valor):
    return logica.formato_numero(valor)


@app.template_filter('fecha')
def filtro_fecha(valor):
    return logica.formato_fecha(valor)


@app.template_filter('clase_estado')
def filtro_clase_estado(estado):
    verdes = ['Normal', 'Liberado', 'Entregado', 'Terminada', 'Activo', 'Óptimo', 'Alcanza', 'Atendida', 'Surtido']
    amarillos = ['Por caducar', 'En preparación', 'En proceso', 'Programada', 'Pendiente de inspección', 'Pendiente',
                 'Precaución', 'Registrado', 'Retenido', 'Programado']
    rojos = ['Bajo el mínimo', 'Rechazado', 'Caducado', 'Falta', 'Crítico', 'Bloqueado']
    azules = ['En tránsito', 'Enviado']
    if estado in verdes:
        return 'etiqueta verde'
    if estado in amarillos:
        return 'etiqueta amarilla'
    if estado in rojos:
        return 'etiqueta roja'
    if estado in azules:
        return 'etiqueta azul'
    return 'etiqueta gris'


@app.context_processor
def datos_generales():
    return {
        'usuario': seguridad.usuario_actual(),
        'menu': seguridad.menu_del_usuario(),
        'nombre_rol': seguridad.NOMBRES_ROL.get(session.get('rol', ''), ''),
        'puede': seguridad.puede,
        'folio': seguridad.folio,
        'motor_bd': 'MySQL' if config.MOTOR == 'mysql' else 'SQLite',
    }


@app.errorhandler(403)
def sin_permiso(error):
    return render_template('error.html', titulo='Sin permiso',
                           mensaje='Tu perfil no tiene acceso a esta opción.'), 403


@app.errorhandler(404)
def no_encontrado(error):
    return render_template('error.html', titulo='No encontrado',
                           mensaje='La página o el registro que buscas no existe.'), 404


@app.route('/')
def raiz():
    if 'usuario_id' in session:
        return redirect(url_for('panel'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip().lower()
        contrasena = request.form.get('contrasena', '')
        persona = db.consultar_uno('SELECT * FROM usuarios WHERE correo = %s', (correo,))
        if persona is None:
            flash('Usuario o contraseña incorrectos.', 'error')
            return render_template('login.html', correo=correo)
        if persona['activo'] != 1:
            flash('Esta cuenta está desactivada. Consulta al administrador.', 'error')
            return render_template('login.html', correo=correo)
        if persona['bloqueado_hasta'] and persona['bloqueado_hasta'] > db.ahora():
            flash('Cuenta bloqueada por intentos fallidos. Intenta después de las ' + persona['bloqueado_hasta'][11:16] + '.', 'error')
            return render_template('login.html', correo=correo)
        if not check_password_hash(persona['contrasena'], contrasena):
            intentos = persona['intentos_fallidos'] + 1
            if intentos >= config.INTENTOS_MAXIMOS:
                hasta = (datetime.datetime.now() + datetime.timedelta(minutes=config.MINUTOS_BLOQUEO)).strftime('%Y-%m-%d %H:%M:%S')
                db.ejecutar('UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = %s WHERE id = %s', (hasta, persona['id']))
                flash('Se bloqueó la cuenta por ' + str(config.MINUTOS_BLOQUEO) + ' minutos después de ' + str(config.INTENTOS_MAXIMOS) + ' intentos fallidos.', 'error')
            else:
                db.ejecutar('UPDATE usuarios SET intentos_fallidos = %s WHERE id = %s', (intentos, persona['id']))
                restantes = config.INTENTOS_MAXIMOS - intentos
                flash('Usuario o contraseña incorrectos. Te quedan ' + str(restantes) + ' intentos.', 'error')
            return render_template('login.html', correo=correo)
        db.ejecutar('UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = %s', (persona['id'],))
        session.clear()
        session['usuario_id'] = persona['id']
        session['nombre'] = persona['nombre']
        session['rol'] = persona['rol']
        seguridad.registrar_bitacora('Inició sesión', 'usuarios')
        return redirect(url_for('panel'))
    return render_template('login.html', correo='')


@app.route('/salir')
def salir():
    if 'usuario_id' in session:
        seguridad.registrar_bitacora('Cerró sesión', 'usuarios')
    session.clear()
    flash('Sesión cerrada.', 'ok')
    return redirect(url_for('login'))


@app.route('/panel')
@seguridad.requiere_sesion
def panel():
    rol = session['rol']
    alertas = []

    if rol in ('almacen', 'compras', 'gerente', 'produccion'):
        for articulo in logica.articulos_bajo_minimo():
            if rol == 'produccion' and articulo['tipo'] == 'Producto terminado':
                continue
            alertas.append({'tipo': 'Bajo el mínimo', 'texto': articulo['nombre'],
                            'detalle': logica.formato_numero(articulo['existencia']) + ' ' + articulo['unidad'] + ' (mínimo ' + logica.formato_numero(articulo['nivel_minimo']) + ')',
                            'enlace': enlace('inventarios.inicio', buscar=articulo['codigo'])})

    if rol in ('almacen', 'gerente', 'calidad'):
        for lote in logica.lotes_por_caducar():
            alertas.append({'tipo': 'Por caducar', 'texto': lote['articulo'] + ' · lote ' + lote['numero_lote'],
                            'detalle': 'Caduca el ' + logica.formato_fecha(lote['fecha_caducidad']),
                            'enlace': enlace('inventarios.inicio', buscar=lote['numero_lote']) if seguridad.puede('inventarios') else None})

    if rol == 'almacen':
        pedidos = db.consultar("SELECT p.id, p.estado, p.fecha_requerida, c.nombre AS cliente FROM pedidos p JOIN clientes c ON c.id = p.cliente_id "
                               "WHERE p.estado IN ('Registrado', 'En preparación') ORDER BY p.fecha_requerida")
        for p in pedidos:
            alertas.append({'tipo': 'Pendiente', 'texto': 'Pedido ' + seguridad.folio('PED', p['id']) + ' por surtir',
                            'detalle': p['cliente'] + ' · requerido el ' + logica.formato_fecha(p['fecha_requerida']),
                            'enlace': enlace('almacen.surtir', pedido_id=p['id'])})

    if rol in ('produccion', 'ventas'):
        avisos = db.consultar("SELECT * FROM avisos WHERE rol_destino = %s AND estado = 'Pendiente' ORDER BY id DESC", (rol,))
        for a in avisos:
            alertas.append({'tipo': 'Falta', 'texto': a['tipo'], 'detalle': a['mensaje'],
                            'enlace': enlace('produccion.inicio', pedido_id=a['pedido_id']) if rol == 'produccion' else None,
                            'aviso_id': a['id']})

    if rol == 'calidad':
        pendientes = db.consultar("SELECT l.numero_lote, a.nombre FROM lotes l JOIN articulos a ON a.id = l.articulo_id WHERE l.estado_calidad = 'Pendiente'")
        for l in pendientes:
            alertas.append({'tipo': 'Pendiente de inspección', 'texto': l['nombre'], 'detalle': 'Lote ' + l['numero_lote'],
                            'enlace': enlace('calidad.inicio')})

    if rol == 'logistica':
        surtidos = db.consultar("SELECT p.id, c.nombre AS cliente FROM pedidos p JOIN clientes c ON c.id = p.cliente_id "
                                "WHERE p.estado = 'Surtido' AND NOT EXISTS (SELECT 1 FROM envios e WHERE e.pedido_id = p.id) ORDER BY p.id")
        for p in surtidos:
            alertas.append({'tipo': 'Pendiente', 'texto': 'Pedido ' + seguridad.folio('PED', p['id']) + ' listo para envío',
                            'detalle': p['cliente'], 'enlace': enlace('logistica.inicio', pedido_id=p['id'])})

    if rol == 'admin':
        bloqueados = db.consultar('SELECT nombre, correo FROM usuarios WHERE bloqueado_hasta IS NOT NULL AND bloqueado_hasta > %s', (db.ahora(),))
        for b in bloqueados:
            alertas.append({'tipo': 'Bloqueado', 'texto': b['nombre'], 'detalle': b['correo'], 'enlace': enlace('usuarios.inicio')})

    return render_template('panel.html', alertas=alertas)


@app.route('/aviso/<int:aviso_id>/atender', methods=['POST'])
@seguridad.requiere_sesion
def atender_aviso(aviso_id):
    db.ejecutar("UPDATE avisos SET estado = 'Atendido' WHERE id = %s AND rol_destino = %s", (aviso_id, session['rol']))
    seguridad.registrar_bitacora('Marcó como atendido el aviso ' + str(aviso_id), 'avisos')
    flash('Aviso marcado como atendido.', 'ok')
    return redirect(url_for('panel'))


def preparar_base_de_datos():
    print('')
    print('=== Herdez SCM ===')
    if config.MOTOR == 'mysql' and not db.probar_mysql():
        try:
            conexion = db.conectar_mysql(con_base=False)
            conexion.close()
            print('  MySQL sí responde, pero falta crear la base. Creándola...')
            import crear_bd
            crear_bd.principal()
        except Exception:
            print('  Se usará SQLite para que el prototipo funcione sin MySQL.')
            config.MOTOR = 'sqlite'
    tiene_tablas = True
    conexion = db.nueva_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute('SELECT COUNT(*) FROM usuarios')
        cursor.close()
    except Exception:
        tiene_tablas = False
    finally:
        conexion.close()
    if not tiene_tablas:
        print('  La base de datos no tiene tablas. Creándola con datos de prueba...')
        import crear_bd
        crear_bd.principal()
    print('  Base de datos:', 'MySQL' if config.MOTOR == 'mysql' else 'SQLite')
    print('  Abre en el navegador:  http://localhost:5000')
    print('')


if __name__ == '__main__':
    preparar_base_de_datos()
    app.run(host='0.0.0.0', port=5000, debug=False)
