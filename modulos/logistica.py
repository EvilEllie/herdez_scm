from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
import db
import seguridad

bp = Blueprint('logistica', __name__, url_prefix='/logistica')


@bp.route('/')
@seguridad.requiere_modulo('logistica')
def inicio():
    surtidos = db.consultar("SELECT p.id, c.nombre AS cliente, c.direccion FROM pedidos p JOIN clientes c ON c.id = p.cliente_id "
                            "WHERE p.estado = 'Surtido' AND NOT EXISTS (SELECT 1 FROM envios e WHERE e.pedido_id = p.id) ORDER BY p.id")
    rutas = db.consultar('SELECT * FROM rutas ORDER BY nombre')
    envios = db.consultar("SELECT e.*, r.nombre AS ruta, c.nombre AS cliente FROM envios e JOIN rutas r ON r.id = e.ruta_id "
                          "JOIN pedidos p ON p.id = e.pedido_id JOIN clientes c ON c.id = p.cliente_id "
                          "ORDER BY CASE e.estado WHEN 'Programado' THEN 0 WHEN 'En tránsito' THEN 1 ELSE 2 END, e.id DESC")

    elegido = request.args.get('pedido_id', '')
    destino = ''
    for s in surtidos:
        if str(s['id']) == elegido:
            destino = s['direccion']

    lote_buscado = request.args.get('lote', '').strip().upper()
    rastreo = None
    lote = None
    if lote_buscado != '':
        lote = db.consultar_uno('SELECT l.*, a.nombre FROM lotes l JOIN articulos a ON a.id = l.articulo_id WHERE UPPER(l.numero_lote) = %s',
                                (lote_buscado,))
        rastreo = db.consultar("SELECT m.cantidad, m.fecha, p.id AS pedido_id, c.nombre AS cliente, e.destino, e.estado, e.fecha_entrega, r.nombre AS ruta "
                               "FROM movimientos_almacen m JOIN lotes l ON l.id = m.lote_id JOIN pedidos p ON p.id = m.pedido_id "
                               "JOIN clientes c ON c.id = p.cliente_id LEFT JOIN envios e ON e.pedido_id = p.id LEFT JOIN rutas r ON r.id = e.ruta_id "
                               "WHERE m.tipo = 'Salida' AND UPPER(l.numero_lote) = %s ORDER BY m.fecha", (lote_buscado,))
    return render_template('logistica/inicio.html', surtidos=surtidos, rutas=rutas, envios=envios, elegido=elegido, destino=destino,
                           lote_buscado=lote_buscado, lote=lote, rastreo=rastreo, hoy=db.hoy())


@bp.route('/nuevo', methods=['POST'])
@seguridad.requiere_modulo('logistica', 'registrar')
def nuevo():
    pedido_id = request.form.get('pedido_id', '')
    ruta_id = request.form.get('ruta_id', '')
    destino = request.form.get('destino', '').strip()
    fecha_salida = request.form.get('fecha_salida', '')
    if pedido_id == '' or ruta_id == '' or destino == '' or fecha_salida == '':
        flash('Llena todos los datos del envío.', 'error')
        return redirect(url_for('logistica.inicio'))
    pedido = db.consultar_uno('SELECT * FROM pedidos WHERE id = %s', (pedido_id,))
    if pedido is None or pedido['estado'] != 'Surtido':
        flash('Solo se pueden enviar pedidos surtidos.', 'error')
        return redirect(url_for('logistica.inicio'))
    if db.consultar_uno('SELECT id FROM envios WHERE pedido_id = %s', (pedido_id,)) is not None:
        flash('Ese pedido ya tiene un envío programado.', 'error')
        return redirect(url_for('logistica.inicio'))
    envio_id = db.ejecutar("INSERT INTO envios (pedido_id, ruta_id, destino, fecha_salida, estado) VALUES (%s, %s, %s, %s, 'Programado')",
                           (pedido_id, ruta_id, destino, fecha_salida))
    seguridad.registrar_bitacora('Programó el envío ' + seguridad.folio('ENV', envio_id) + ' del pedido ' + seguridad.folio('PED', pedido_id), 'envios')
    flash('Envío ' + seguridad.folio('ENV', envio_id) + ' programado para el pedido ' + seguridad.folio('PED', pedido_id) + '.', 'ok')
    return redirect(url_for('logistica.inicio'))


@bp.route('/<int:envio_id>/estado', methods=['POST'])
@seguridad.requiere_modulo('logistica', 'registrar')
def cambiar_estado(envio_id):
    envio = db.consultar_uno('SELECT * FROM envios WHERE id = %s', (envio_id,))
    if envio is None:
        abort(404)
    nuevo_estado = request.form.get('estado', '')
    if envio['estado'] == 'Programado' and nuevo_estado == 'En tránsito':
        db.ejecutar("UPDATE envios SET estado = 'En tránsito' WHERE id = %s", (envio_id,))
        db.ejecutar("UPDATE pedidos SET estado = 'Enviado' WHERE id = %s", (envio['pedido_id'],))
    elif envio['estado'] == 'En tránsito' and nuevo_estado == 'Entregado':
        db.ejecutar("UPDATE envios SET estado = 'Entregado', fecha_entrega = %s WHERE id = %s", (db.hoy(), envio_id))
        db.ejecutar("UPDATE pedidos SET estado = 'Entregado' WHERE id = %s", (envio['pedido_id'],))
    else:
        flash('Ese cambio de estado no es válido.', 'error')
        return redirect(url_for('logistica.inicio'))
    seguridad.registrar_bitacora('Cambió el envío ' + seguridad.folio('ENV', envio_id) + ' a ' + nuevo_estado, 'envios')
    flash('Envío ' + seguridad.folio('ENV', envio_id) + ': ' + nuevo_estado + '. El pedido ' + seguridad.folio('PED', envio['pedido_id']) + ' se actualizó.', 'ok')
    return redirect(url_for('logistica.inicio'))
