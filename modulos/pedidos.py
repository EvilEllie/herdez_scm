from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
import db
import logica
import seguridad

bp = Blueprint('pedidos', __name__, url_prefix='/pedidos')


def productos_con_disponibilidad():
    productos = db.consultar("SELECT id, codigo, nombre FROM articulos WHERE tipo = 'Producto terminado' ORDER BY codigo")
    for p in productos:
        p['disponible'] = logica.existencia_disponible(p['id'])
    return productos


@bp.route('/')
@seguridad.requiere_modulo('pedidos')
def inicio():
    estado = request.args.get('estado', '')
    sql = ("SELECT p.*, c.nombre AS cliente, "
           "(SELECT SUM(d.cantidad) FROM detalle_pedido d WHERE d.pedido_id = p.id) AS cajas "
           "FROM pedidos p JOIN clientes c ON c.id = p.cliente_id")
    parametros = ()
    if estado != '':
        sql = sql + ' WHERE p.estado = %s'
        parametros = (estado,)
    sql = sql + ' ORDER BY p.id DESC'
    pedidos = db.consultar(sql, parametros)
    clientes = db.consultar('SELECT id, nombre FROM clientes ORDER BY nombre')
    productos = productos_con_disponibilidad()
    disponibles = {}
    for p in productos:
        disponibles[str(p['id'])] = p['disponible']
    return render_template('pedidos/inicio.html', pedidos=pedidos, clientes=clientes, productos=productos,
                           disponibles=disponibles, estado=estado, hoy=db.hoy(),
                           estados=['Registrado', 'En preparación', 'Surtido', 'Enviado', 'Entregado'])


@bp.route('/nuevo', methods=['POST'])
@seguridad.requiere_modulo('pedidos', 'registrar')
def nuevo():
    cliente_id = request.form.get('cliente_id', '')
    fecha_requerida = request.form.get('fecha_requerida', '')
    productos = request.form.getlist('producto_id')
    cantidades = request.form.getlist('cantidad')

    if cliente_id == '' or fecha_requerida == '':
        flash('Selecciona el cliente y la fecha requerida.', 'error')
        return redirect(url_for('pedidos.inicio'))
    if fecha_requerida < db.hoy():
        flash('La fecha requerida no puede ser anterior a hoy.', 'error')
        return redirect(url_for('pedidos.inicio'))

    lineas = {}
    for i in range(len(productos)):
        if productos[i] == '' or i >= len(cantidades) or cantidades[i].strip() == '':
            continue
        try:
            cantidad = float(cantidades[i])
        except ValueError:
            flash('Escribe cantidades con número.', 'error')
            return redirect(url_for('pedidos.inicio'))
        if cantidad <= 0:
            continue
        lineas[productos[i]] = lineas.get(productos[i], 0) + cantidad
    if len(lineas) == 0:
        flash('Agrega al menos un producto con cantidad.', 'error')
        return redirect(url_for('pedidos.inicio'))

    pedido_id = db.ejecutar(
        "INSERT INTO pedidos (cliente_id, fecha_registro, fecha_requerida, estado, usuario_id) VALUES (%s, %s, %s, 'Registrado', %s)",
        (cliente_id, db.hoy(), fecha_requerida, session['usuario_id']))
    faltantes = []
    for producto_id in lineas:
        db.ejecutar('INSERT INTO detalle_pedido (pedido_id, articulo_id, cantidad) VALUES (%s, %s, %s)',
                    (pedido_id, producto_id, lineas[producto_id]))
        disponible = logica.existencia_disponible(producto_id)
        if disponible < lineas[producto_id]:
            articulo = db.consultar_uno('SELECT nombre FROM articulos WHERE id = %s', (producto_id,))
            falta = lineas[producto_id] - disponible
            faltantes.append(logica.formato_numero(falta) + ' cajas de ' + articulo['nombre'])

    numero = seguridad.folio('PED', pedido_id)
    seguridad.registrar_bitacora('Registró el pedido ' + numero, 'pedidos')

    if len(faltantes) > 0:
        mensaje = 'Pedido ' + numero + ': faltan ' + ', '.join(faltantes) + '.'
        db.ejecutar("INSERT INTO avisos (tipo, mensaje, rol_destino, fecha, estado, pedido_id) VALUES ('Falta de producto', %s, 'produccion', %s, 'Pendiente', %s)",
                    (mensaje, db.hoy(), pedido_id))
        seguridad.registrar_bitacora('Avisó a Producción por faltante en ' + numero, 'avisos')
        flash('Pedido ' + numero + ' registrado. No alcanza la existencia: faltan ' + ', '.join(faltantes) + '. Se envió un aviso a Producción.', 'aviso')
    else:
        flash('Pedido ' + numero + ' registrado. Hay existencia para surtirlo completo.', 'ok')
    return redirect(url_for('pedidos.detalle', pedido_id=pedido_id))


@bp.route('/<int:pedido_id>')
@seguridad.requiere_modulo('pedidos')
def detalle(pedido_id):
    pedido = db.consultar_uno('SELECT p.*, c.nombre AS cliente, c.direccion, u.nombre AS registro FROM pedidos p '
                              'JOIN clientes c ON c.id = p.cliente_id LEFT JOIN usuarios u ON u.id = p.usuario_id WHERE p.id = %s',
                              (pedido_id,))
    if pedido is None:
        abort(404)
    lineas = db.consultar('SELECT d.*, a.codigo, a.nombre FROM detalle_pedido d JOIN articulos a ON a.id = d.articulo_id WHERE d.pedido_id = %s',
                          (pedido_id,))
    for linea in lineas:
        linea['disponible'] = logica.existencia_disponible(linea['articulo_id'])
    salidas = db.consultar("SELECT m.*, l.numero_lote, l.fecha_caducidad, a.nombre FROM movimientos_almacen m "
                           "JOIN lotes l ON l.id = m.lote_id JOIN articulos a ON a.id = l.articulo_id "
                           "WHERE m.pedido_id = %s AND m.tipo = 'Salida' ORDER BY m.id", (pedido_id,))
    envio = db.consultar_uno('SELECT e.*, r.nombre AS ruta FROM envios e JOIN rutas r ON r.id = e.ruta_id WHERE e.pedido_id = %s ORDER BY e.id DESC',
                             (pedido_id,))
    pasos = ['Registrado', 'En preparación', 'Surtido', 'Enviado', 'Entregado']
    return render_template('pedidos/detalle.html', pedido=pedido, lineas=lineas, salidas=salidas, envio=envio, pasos=pasos)
