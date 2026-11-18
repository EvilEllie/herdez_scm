from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
import db
import logica
import seguridad

bp = Blueprint('produccion', __name__, url_prefix='/produccion')


def datos_pantalla():
    productos = db.consultar("SELECT id, codigo, nombre FROM articulos WHERE tipo = 'Producto terminado' ORDER BY codigo")
    pedidos = db.consultar("SELECT p.id, c.nombre AS cliente FROM pedidos p JOIN clientes c ON c.id = p.cliente_id "
                           "WHERE p.estado IN ('Registrado', 'En preparación') ORDER BY p.id DESC")
    ordenes = db.consultar("SELECT o.*, a.nombre AS producto, a.codigo, l.numero_lote FROM ordenes_produccion o "
                           "JOIN articulos a ON a.id = o.articulo_id LEFT JOIN lotes l ON l.orden_id = o.id "
                           "ORDER BY CASE o.estado WHEN 'En proceso' THEN 0 WHEN 'Programada' THEN 1 ELSE 2 END, o.id DESC")
    for o in ordenes:
        if o['estado'] != 'Terminada':
            o['alcanza'] = logica.todo_alcanza(logica.verificar_materiales(o['articulo_id'], o['cantidad_planeada']))
    avisos = db.consultar("SELECT * FROM avisos WHERE rol_destino = 'produccion' AND estado = 'Pendiente' ORDER BY id DESC")
    return productos, pedidos, ordenes, avisos


def sugerencia_por_pedido(pedido_id):
    lineas = db.consultar('SELECT articulo_id, cantidad FROM detalle_pedido WHERE pedido_id = %s', (pedido_id,))
    for linea in lineas:
        disponible = logica.existencia_disponible(linea['articulo_id'])
        if disponible < float(linea['cantidad']):
            return {'producto_id': str(linea['articulo_id']), 'cantidad': int(float(linea['cantidad']) - disponible + 0.999)}
    return None


@bp.route('/')
@seguridad.requiere_modulo('produccion')
def inicio():
    productos, pedidos, ordenes, avisos = datos_pantalla()
    formulario = {'producto_id': '', 'cantidad': '', 'pedido_id': '', 'fecha': db.hoy()}
    pedido_id = request.args.get('pedido_id', '')
    if pedido_id not in ('', 'None'):
        sugerencia = sugerencia_por_pedido(pedido_id)
        formulario['pedido_id'] = pedido_id
        if sugerencia is not None:
            formulario['producto_id'] = sugerencia['producto_id']
            formulario['cantidad'] = sugerencia['cantidad']
    return render_template('produccion/inicio.html', productos=productos, pedidos=pedidos, ordenes=ordenes, avisos=avisos,
                           formulario=formulario, verificacion=None)


def leer_formulario():
    formulario = {
        'producto_id': request.form.get('producto_id', ''),
        'cantidad': request.form.get('cantidad', ''),
        'pedido_id': request.form.get('pedido_id', ''),
        'fecha': request.form.get('fecha', db.hoy()),
    }
    error = None
    if formulario['producto_id'] == '':
        error = 'Selecciona el producto.'
    else:
        try:
            if float(formulario['cantidad']) <= 0:
                error = 'La cantidad debe ser mayor a cero.'
        except ValueError:
            error = 'Escribe la cantidad de cajas.'
    return formulario, error


@bp.route('/verificar', methods=['POST'])
@seguridad.requiere_modulo('produccion', 'registrar')
def verificar():
    formulario, error = leer_formulario()
    productos, pedidos, ordenes, avisos = datos_pantalla()
    verificacion = None
    if error:
        flash(error, 'error')
    else:
        verificacion = logica.verificar_materiales(formulario['producto_id'], formulario['cantidad'])
    return render_template('produccion/inicio.html', productos=productos, pedidos=pedidos, ordenes=ordenes, avisos=avisos,
                           formulario=formulario, verificacion=verificacion)


@bp.route('/nueva', methods=['POST'])
@seguridad.requiere_modulo('produccion', 'registrar')
def nueva():
    formulario, error = leer_formulario()
    if error:
        flash(error, 'error')
        return redirect(url_for('produccion.inicio'))
    pedido_id = formulario['pedido_id'] if formulario['pedido_id'] != '' else None
    orden_id = db.ejecutar("INSERT INTO ordenes_produccion (articulo_id, cantidad_planeada, cantidad_producida, pedido_id, fecha_programada, estado, usuario_id) "
                           "VALUES (%s, %s, 0, %s, %s, 'Programada', %s)",
                           (formulario['producto_id'], formulario['cantidad'], pedido_id, formulario['fecha'], session['usuario_id']))
    numero = seguridad.folio('OP', orden_id)
    seguridad.registrar_bitacora('Creó la orden de producción ' + numero, 'ordenes_produccion')
    verificacion = logica.verificar_materiales(formulario['producto_id'], formulario['cantidad'])
    if logica.todo_alcanza(verificacion):
        flash('Orden ' + numero + ' creada. Los materiales alcanzan.', 'ok')
    else:
        faltan = []
        for v in verificacion:
            if not v['alcanza']:
                faltan.append(v['nombre'])
        flash('Orden ' + numero + ' creada, pero faltan materiales: ' + ', '.join(faltan) + '. No se podrá iniciar hasta reabastecer.', 'aviso')
    return redirect(url_for('produccion.inicio'))


@bp.route('/<int:orden_id>/iniciar', methods=['POST'])
@seguridad.requiere_modulo('produccion', 'registrar')
def iniciar(orden_id):
    orden = db.consultar_uno('SELECT * FROM ordenes_produccion WHERE id = %s', (orden_id,))
    if orden is None:
        abort(404)
    verificacion = logica.verificar_materiales(orden['articulo_id'], orden['cantidad_planeada'])
    if not logica.todo_alcanza(verificacion):
        flash('No se puede iniciar ' + seguridad.folio('OP', orden_id) + ': faltan materiales. Pide reabastecimiento a Compras.', 'error')
        return redirect(url_for('produccion.inicio'))
    db.ejecutar("UPDATE ordenes_produccion SET estado = 'En proceso' WHERE id = %s", (orden_id,))
    seguridad.registrar_bitacora('Inició la orden ' + seguridad.folio('OP', orden_id), 'ordenes_produccion')
    flash('Orden ' + seguridad.folio('OP', orden_id) + ' en proceso.', 'ok')
    return redirect(url_for('produccion.inicio'))


def siguiente_numero_lote():
    prefijo = 'L' + db.hoy().replace('-', '')[2:] + '-'
    filas = db.consultar('SELECT numero_lote FROM lotes WHERE numero_lote LIKE %s', (prefijo + '%',))
    mayor = 0
    for fila in filas:
        try:
            mayor = max(mayor, int(fila['numero_lote'].split('-')[1]))
        except (IndexError, ValueError):
            pass
    return prefijo + str(mayor + 1).zfill(2)


@bp.route('/<int:orden_id>/registrar', methods=['POST'])
@seguridad.requiere_modulo('produccion', 'registrar')
def registrar(orden_id):
    orden = db.consultar_uno('SELECT o.*, a.nombre, a.vida_util_dias FROM ordenes_produccion o JOIN articulos a ON a.id = o.articulo_id WHERE o.id = %s',
                             (orden_id,))
    if orden is None:
        abort(404)
    if orden['estado'] != 'En proceso':
        flash('Primero inicia la orden.', 'error')
        return redirect(url_for('produccion.inicio'))
    try:
        producida = float(request.form.get('cantidad_producida', ''))
    except ValueError:
        flash('Escribe la cantidad producida.', 'error')
        return redirect(url_for('produccion.inicio'))
    if producida <= 0:
        flash('La cantidad producida debe ser mayor a cero.', 'error')
        return redirect(url_for('produccion.inicio'))

    verificacion = logica.verificar_materiales(orden['articulo_id'], producida)
    if not logica.todo_alcanza(verificacion):
        flash('No alcanzan los materiales para ' + logica.formato_numero(producida) + ' cajas.', 'error')
        return redirect(url_for('produccion.inicio'))

    numero_lote = siguiente_numero_lote()
    planta = db.consultar_uno("SELECT id FROM sedes WHERE tipo = 'Planta' ORDER BY id")
    db.ejecutar("INSERT INTO lotes (numero_lote, articulo_id, sede_id, ubicacion, cantidad, fecha_entrada, fecha_caducidad, estado_calidad, orden_id) "
                          "VALUES (%s, %s, %s, 'Por asignar', %s, %s, %s, 'Pendiente', %s)",
                          (numero_lote, orden['articulo_id'], planta['id'], producida, db.hoy(),
                           db.sumar_dias(db.hoy(), orden['vida_util_dias']), orden_id))

    for material in verificacion:
        asignaciones, faltante = logica.asignar_fefo(material['material_id'], material['necesario'])
        for a in asignaciones:
            db.ejecutar('UPDATE lotes SET cantidad = cantidad - %s WHERE id = %s', (a['cantidad'], a['lote']['id']))
            db.ejecutar('INSERT INTO consumos_produccion (orden_id, lote_id, cantidad) VALUES (%s, %s, %s)', (orden_id, a['lote']['id'], a['cantidad']))
            db.ejecutar("INSERT INTO movimientos_almacen (tipo, lote_id, cantidad, fecha, usuario_id) VALUES ('Consumo', %s, %s, %s, %s)",
                        (a['lote']['id'], a['cantidad'], db.hoy(), session['usuario_id']))

    db.ejecutar("UPDATE ordenes_produccion SET cantidad_producida = %s, fecha_termino = %s, estado = 'Terminada' WHERE id = %s",
                (producida, db.hoy(), orden_id))
    if orden['pedido_id']:
        db.ejecutar("UPDATE avisos SET estado = 'Atendido' WHERE pedido_id = %s AND rol_destino = 'produccion'", (orden['pedido_id'],))
    seguridad.registrar_bitacora('Registró ' + logica.formato_numero(producida) + ' cajas de ' + orden['nombre'] + ' en el lote ' + numero_lote, 'lotes')
    flash('Producción registrada: lote ' + numero_lote + ' con ' + logica.formato_numero(producida) + ' cajas. Queda pendiente de inspección de calidad.', 'ok')
    return redirect(url_for('produccion.inicio'))
