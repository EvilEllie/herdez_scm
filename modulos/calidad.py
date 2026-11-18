from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
import db
import seguridad

bp = Blueprint('calidad', __name__, url_prefix='/calidad')

RESULTADOS = ['Liberado', 'Retenido', 'Rechazado']


@bp.route('/')
@seguridad.requiere_modulo('calidad')
def inicio():
    pendientes = db.consultar("SELECT l.*, a.nombre AS producto, a.codigo, o.id AS orden FROM lotes l "
                              "JOIN articulos a ON a.id = l.articulo_id LEFT JOIN ordenes_produccion o ON o.id = l.orden_id "
                              "WHERE l.estado_calidad IN ('Pendiente', 'Retenido') ORDER BY CASE l.estado_calidad WHEN 'Pendiente' THEN 0 ELSE 1 END, l.id")
    inspecciones = db.consultar("SELECT i.*, l.numero_lote, a.nombre AS producto, u.nombre AS responsable FROM inspecciones_calidad i "
                                "JOIN lotes l ON l.id = i.lote_id JOIN articulos a ON a.id = l.articulo_id "
                                "LEFT JOIN usuarios u ON u.id = i.usuario_id ORDER BY i.id DESC LIMIT 12")
    return render_template('calidad/inicio.html', pendientes=pendientes, inspecciones=inspecciones)


@bp.route('/<int:lote_id>', methods=['POST'])
@seguridad.requiere_modulo('calidad', 'registrar')
def inspeccionar(lote_id):
    resultado = request.form.get('resultado', '')
    observaciones = request.form.get('observaciones', '').strip()
    if resultado not in RESULTADOS:
        flash('Elige un resultado válido.', 'error')
        return redirect(url_for('calidad.inicio'))
    lote = db.consultar_uno('SELECT l.*, a.nombre FROM lotes l JOIN articulos a ON a.id = l.articulo_id WHERE l.id = %s', (lote_id,))
    if lote is None:
        abort(404)
    if resultado != 'Liberado' and observaciones == '':
        flash('Escribe en observaciones el motivo para retener o rechazar el lote.', 'error')
        return redirect(url_for('calidad.inicio'))
    if observaciones == '':
        observaciones = 'Sin observaciones'

    db.ejecutar('INSERT INTO inspecciones_calidad (lote_id, resultado, observaciones, fecha, usuario_id) VALUES (%s, %s, %s, %s, %s)',
                (lote_id, resultado, observaciones, db.hoy(), session['usuario_id']))
    if resultado == 'Liberado':
        db.ejecutar("UPDATE lotes SET estado_calidad = 'Liberado' WHERE id = %s", (lote_id,))
        mensaje = 'Lote ' + lote['numero_lote'] + ' liberado. Ya se puede surtir.'
    else:
        db.ejecutar("UPDATE lotes SET estado_calidad = %s, ubicacion = 'Cuarentena' WHERE id = %s", (resultado, lote_id))
        mensaje = 'Lote ' + lote['numero_lote'] + ' ' + resultado.lower() + '. No se podrá surtir.'
    seguridad.registrar_bitacora('Marcó el lote ' + lote['numero_lote'] + ' como ' + resultado, 'inspecciones_calidad')
    flash(mensaje, 'ok' if resultado == 'Liberado' else 'aviso')
    return redirect(url_for('calidad.inicio'))
