from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
import db
import logica
import seguridad

bp = Blueprint('almacen', __name__, url_prefix='/almacen')


def armar_surtido(pedido_id):
    lineas = db.consultar('SELECT d.articulo_id, d.cantidad, a.nombre, a.codigo FROM detalle_pedido d '
                          'JOIN articulos a ON a.id = d.articulo_id WHERE d.pedido_id = %s ORDER BY d.id', (pedido_id,))
    renglones = []
    faltantes = []
    for linea in lineas:
        asignaciones, faltante = logica.asignar_fefo(linea['articulo_id'], linea['cantidad'])
        for a in asignaciones:
            renglones.append({
                'clave': str(linea['articulo_id']) + '-' + str(a['lote']['id']),
                'producto': linea['nombre'],
                'lote_id': a['lote']['id'],
                'numero_lote': a['lote']['numero_lote'],
                'ubicacion': a['lote']['ubicacion'],
                'caducidad': a['lote']['fecha_caducidad'],
                'cantidad': a['cantidad'],
            })
        if faltante > 0:
            faltantes.append({'producto': linea['nombre'], 'cantidad': faltante})
    return renglones, faltantes


def confirmados(pedido_id):
    todos = session.get('surtido', {})
    return todos.get(str(pedido_id), [])


def guardar_confirmado(pedido_id, clave):
    todos = session.get('surtido', {})
    lista = todos.get(str(pedido_id), [])
    if clave not in lista:
        lista.append(clave)
    todos[str(pedido_id)] = lista
    session['surtido'] = todos


@bp.route('/surtido')
@seguridad.requiere_modulo('almacen')
def surtido():
    pedidos = db.consultar("SELECT p.*, c.nombre AS cliente, (SELECT SUM(d.cantidad) FROM detalle_pedido d WHERE d.pedido_id = p.id) AS cajas "
                           "FROM pedidos p JOIN clientes c ON c.id = p.cliente_id "
                           "WHERE p.estado IN ('Registrado', 'En preparación') ORDER BY p.fecha_requerida, p.id")
    return render_template('almacen/surtido_lista.html', pedidos=pedidos, pestana='surtido')


@bp.route('/surtido/<int:pedido_id>')
@seguridad.requiere_modulo('almacen')
def surtir(pedido_id):
    pedido = db.consultar_uno('SELECT p.*, c.nombre AS cliente FROM pedidos p JOIN clientes c ON c.id = p.cliente_id WHERE p.id = %s', (pedido_id,))
    if pedido is None:
        abort(404)
    if pedido['estado'] not in ('Registrado', 'En preparación'):
        flash('El pedido ' + seguridad.folio('PED', pedido_id) + ' ya está ' + pedido['estado'].lower() + '.', 'aviso')
        return redirect(url_for('almacen.surtido'))
    if pedido['estado'] == 'Registrado' and seguridad.puede('almacen', 'registrar'):
        db.ejecutar("UPDATE pedidos SET estado = 'En preparación' WHERE id = %s", (pedido_id,))
        seguridad.registrar_bitacora('Inició el surtido del pedido ' + seguridad.folio('PED', pedido_id), 'pedidos')
        pedido['estado'] = 'En preparación'
    renglones, faltantes = armar_surtido(pedido_id)
    listos = confirmados(pedido_id)
    for r in renglones:
        r['confirmado'] = r['clave'] in listos
    completo = len(faltantes) == 0 and len(renglones) > 0
    for r in renglones:
        if not r['confirmado']:
            completo = False
    return render_template('almacen/surtir.html', pedido=pedido, renglones=renglones, faltantes=faltantes,
                           completo=completo, pestana='surtido')


@bp.route('/surtido/<int:pedido_id>/confirmar', methods=['POST'])
@seguridad.requiere_modulo('almacen', 'registrar')
def confirmar(pedido_id):
    guardar_confirmado(pedido_id, request.form.get('clave', ''))
    return redirect(url_for('almacen.surtir', pedido_id=pedido_id))


@bp.route('/surtido/<int:pedido_id>/escanear', methods=['POST'])
@seguridad.requiere_modulo('almacen', 'registrar')
def escanear(pedido_id):
    codigo = request.form.get('codigo', '').strip().upper()
    if codigo == '':
        flash('Escanea o escribe el número de lote.', 'error')
        return redirect(url_for('almacen.surtir', pedido_id=pedido_id))
    renglones, faltantes = armar_surtido(pedido_id)
    for r in renglones:
        if r['numero_lote'].upper() == codigo:
            guardar_confirmado(pedido_id, r['clave'])
            flash('Lote ' + r['numero_lote'] + ' confirmado: ' + logica.formato_numero(r['cantidad']) + ' cajas de ' + r['producto'] + '.', 'ok')
            return redirect(url_for('almacen.surtir', pedido_id=pedido_id))
    lote = db.consultar_uno('SELECT * FROM lotes WHERE UPPER(numero_lote) = %s', (codigo,))
    if lote is None:
        flash('El lote ' + codigo + ' no existe.', 'error')
    elif lote['estado_calidad'] != 'Liberado':
        flash('El lote ' + codigo + ' está ' + lote['estado_calidad'].lower() + ' por Calidad: no se puede surtir.', 'error')
    else:
        flash('El lote ' + codigo + ' no es el indicado: surte primero los lotes de la lista, que caducan antes.', 'error')
    return redirect(url_for('almacen.surtir', pedido_id=pedido_id))


@bp.route('/surtido/<int:pedido_id>/salida', methods=['POST'])
@seguridad.requiere_modulo('almacen', 'registrar')
def registrar_salida(pedido_id):
    pedido = db.consultar_uno('SELECT * FROM pedidos WHERE id = %s', (pedido_id,))
    if pedido is None or pedido['estado'] not in ('Registrado', 'En preparación'):
        flash('Ese pedido ya no se puede surtir.', 'error')
        return redirect(url_for('almacen.surtido'))
    renglones, faltantes = armar_surtido(pedido_id)
    if len(faltantes) > 0:
        flash('No hay existencia suficiente para surtir completo. Espera la producción.', 'error')
        return redirect(url_for('almacen.surtir', pedido_id=pedido_id))
    listos = confirmados(pedido_id)
    for r in renglones:
        if r['clave'] not in listos:
            flash('Confirma todos los lotes antes de registrar la salida.', 'error')
            return redirect(url_for('almacen.surtir', pedido_id=pedido_id))
    for r in renglones:
        db.ejecutar('UPDATE lotes SET cantidad = cantidad - %s WHERE id = %s', (r['cantidad'], r['lote_id']))
        db.ejecutar("INSERT INTO movimientos_almacen (tipo, lote_id, cantidad, fecha, usuario_id, pedido_id) VALUES ('Salida', %s, %s, %s, %s, %s)",
                    (r['lote_id'], r['cantidad'], db.hoy(), session['usuario_id'], pedido_id))
    db.ejecutar("UPDATE pedidos SET estado = 'Surtido' WHERE id = %s", (pedido_id,))
    todos = session.get('surtido', {})
    todos.pop(str(pedido_id), None)
    session['surtido'] = todos
    seguridad.registrar_bitacora('Registró la salida del pedido ' + seguridad.folio('PED', pedido_id), 'movimientos_almacen')
    flash('Salida registrada. El pedido ' + seguridad.folio('PED', pedido_id) + ' quedó surtido y listo para envío.', 'ok')
    return redirect(url_for('almacen.surtido'))


def siguiente_lote(prefijo_articulo):
    prefijo = prefijo_articulo + '-' + db.hoy().replace('-', '')[2:] + '-'
    filas = db.consultar('SELECT numero_lote FROM lotes WHERE numero_lote LIKE %s', (prefijo + '%',))
    usados = []
    for fila in filas:
        usados.append(fila['numero_lote'])
    numero = len(filas) + 1
    while prefijo + str(numero).zfill(2) in usados:
        numero = numero + 1
    return prefijo + str(numero).zfill(2)


@bp.route('/recepcion', methods=['GET', 'POST'])
@seguridad.requiere_modulo('almacen')
def recepcion():
    if request.method == 'POST':
        if not seguridad.puede('almacen', 'registrar'):
            abort(403)
        articulo_id = request.form.get('articulo_id', '')
        proveedor_id = request.form.get('proveedor_id', '')
        caducidad = request.form.get('fecha_caducidad', '')
        ubicacion = request.form.get('ubicacion', '').strip().upper()
        try:
            cantidad = float(request.form.get('cantidad', ''))
        except ValueError:
            cantidad = 0
        articulo = db.consultar_uno('SELECT * FROM articulos WHERE id = %s', (articulo_id,))
        if articulo is None or proveedor_id == '' or caducidad == '' or ubicacion == '' or cantidad <= 0:
            flash('Llena todos los campos de la recepción.', 'error')
            return redirect(url_for('almacen.recepcion'))
        if caducidad <= db.hoy():
            flash('La fecha de caducidad debe ser posterior a hoy.', 'error')
            return redirect(url_for('almacen.recepcion'))
        numero = siguiente_lote(articulo['codigo'][:2])
        planta = db.consultar_uno("SELECT id FROM sedes WHERE tipo = 'Planta' ORDER BY id")
        lote_id = db.ejecutar("INSERT INTO lotes (numero_lote, articulo_id, sede_id, ubicacion, cantidad, fecha_entrada, fecha_caducidad, estado_calidad, proveedor_id) "
                              "VALUES (%s, %s, %s, %s, %s, %s, %s, 'Liberado', %s)",
                              (numero, articulo_id, planta['id'], ubicacion, cantidad, db.hoy(), caducidad, proveedor_id))
        db.ejecutar("INSERT INTO movimientos_almacen (tipo, lote_id, cantidad, fecha, usuario_id) VALUES ('Entrada', %s, %s, %s, %s)",
                    (lote_id, cantidad, db.hoy(), session['usuario_id']))
        db.ejecutar("UPDATE solicitudes_reabastecimiento SET estado = 'Atendida' WHERE articulo_id = %s AND estado = 'Pendiente'", (articulo_id,))
        seguridad.registrar_bitacora('Recibió ' + logica.formato_numero(cantidad) + ' ' + articulo['unidad'] + ' de ' + articulo['nombre'] + ' (lote ' + numero + ')', 'lotes')
        flash('Recepción registrada en el lote ' + numero + ', ubicación ' + ubicacion + '.', 'ok')
        return redirect(url_for('almacen.recepcion'))

    articulos = db.consultar("SELECT * FROM articulos WHERE tipo <> 'Producto terminado' ORDER BY codigo")
    proveedores = db.consultar('SELECT * FROM proveedores ORDER BY nombre')
    entradas = db.consultar("SELECT m.*, l.numero_lote, l.ubicacion, a.nombre, a.unidad, p.nombre AS proveedor FROM movimientos_almacen m "
                            "JOIN lotes l ON l.id = m.lote_id JOIN articulos a ON a.id = l.articulo_id LEFT JOIN proveedores p ON p.id = l.proveedor_id "
                            "WHERE m.tipo = 'Entrada' AND a.tipo <> 'Producto terminado' ORDER BY m.id DESC LIMIT 8")
    solicitudes = db.consultar("SELECT s.*, a.nombre, a.unidad FROM solicitudes_reabastecimiento s JOIN articulos a ON a.id = s.articulo_id "
                               "WHERE s.estado = 'Pendiente' ORDER BY s.id")
    return render_template('almacen/recepcion.html', articulos=articulos, proveedores=proveedores, entradas=entradas,
                           solicitudes=solicitudes, pestana='recepcion', minimo=db.sumar_dias(db.hoy(), 1))


@bp.route('/ubicacion', methods=['GET', 'POST'])
@seguridad.requiere_modulo('almacen')
def ubicacion():
    if request.method == 'POST':
        if not seguridad.puede('almacen', 'registrar'):
            abort(403)
        lote_id = request.form.get('lote_id', '')
        nueva = request.form.get('ubicacion', '').strip().upper()
        lote = db.consultar_uno('SELECT * FROM lotes WHERE id = %s', (lote_id,))
        if lote is None or nueva == '':
            flash('Escribe la ubicación.', 'error')
            return redirect(url_for('almacen.ubicacion'))
        db.ejecutar('UPDATE lotes SET ubicacion = %s WHERE id = %s', (nueva, lote_id))
        if lote['ubicacion'] == 'Por asignar':
            db.ejecutar("INSERT INTO movimientos_almacen (tipo, lote_id, cantidad, fecha, usuario_id) VALUES ('Entrada', %s, %s, %s, %s)",
                        (lote_id, lote['cantidad'], db.hoy(), session['usuario_id']))
        seguridad.registrar_bitacora('Ubicó el lote ' + lote['numero_lote'] + ' en ' + nueva, 'lotes')
        flash('Lote ' + lote['numero_lote'] + ' ubicado en ' + nueva + '.', 'ok')
        return redirect(url_for('almacen.ubicacion'))

    por_ubicar = db.consultar("SELECT l.*, a.nombre FROM lotes l JOIN articulos a ON a.id = l.articulo_id "
                              "WHERE l.ubicacion = 'Por asignar' AND l.estado_calidad = 'Liberado' AND l.cantidad > 0 ORDER BY l.id")
    en_espera = db.consultar("SELECT l.*, a.nombre FROM lotes l JOIN articulos a ON a.id = l.articulo_id "
                             "WHERE l.estado_calidad = 'Pendiente' ORDER BY l.id")
    return render_template('almacen/ubicacion.html', por_ubicar=por_ubicar, en_espera=en_espera, pestana='ubicacion')
