from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import db
import logica
import seguridad

bp = Blueprint('inventarios', __name__, url_prefix='/inventarios')

TIPOS = ['Producto terminado', 'Materia prima', 'Material de empaque']
ESTADOS = ['Normal', 'Por caducar', 'Bajo el mínimo', 'Pendiente de inspección', 'Retenido', 'Caducado']


@bp.route('/')
@seguridad.requiere_modulo('inventarios')
def inicio():
    tipo = request.args.get('tipo', '')
    estado = request.args.get('estado', '')
    buscar = request.args.get('buscar', '').strip()

    sql = ("SELECT l.*, a.codigo, a.nombre AS articulo, a.tipo, a.unidad, a.nivel_minimo, s.nombre AS sede "
           "FROM lotes l JOIN articulos a ON a.id = l.articulo_id JOIN sedes s ON s.id = l.sede_id "
           "WHERE (l.cantidad > 0 OR l.estado_calidad IN ('Pendiente', 'Retenido'))")
    parametros = []
    if tipo != '':
        sql = sql + ' AND a.tipo = %s'
        parametros.append(tipo)
    if buscar != '':
        sql = sql + ' AND (a.nombre LIKE %s OR a.codigo LIKE %s OR l.numero_lote LIKE %s)'
        texto = '%' + buscar + '%'
        parametros.append(texto)
        parametros.append(texto)
        parametros.append(texto)
    sql = sql + ' ORDER BY a.codigo, l.fecha_caducidad'
    lotes = db.consultar(sql, tuple(parametros))

    totales = {}
    lista = []
    for lote in lotes:
        if lote['articulo_id'] not in totales:
            totales[lote['articulo_id']] = logica.existencia_disponible(lote['articulo_id'])
        lote['estado'] = logica.estado_lote(lote, totales[lote['articulo_id']], lote['nivel_minimo'])
        if estado == '' or lote['estado'] == estado:
            lista.append(lote)

    articulos = db.consultar('SELECT * FROM articulos ORDER BY codigo')
    for a in articulos:
        a['existencia'] = logica.existencia_disponible(a['id'])
        a['bajo'] = a['existencia'] <= float(a['nivel_minimo'])
    solicitudes = db.consultar("SELECT s.*, a.nombre, a.unidad, u.nombre AS usuario FROM solicitudes_reabastecimiento s "
                               "JOIN articulos a ON a.id = s.articulo_id LEFT JOIN usuarios u ON u.id = s.usuario_id ORDER BY s.id DESC")
    return render_template('inventarios/inicio.html', lotes=lista, articulos=articulos, solicitudes=solicitudes,
                           tipos=TIPOS, estados=ESTADOS, tipo=tipo, estado=estado, buscar=buscar)


@bp.route('/minimo/<int:articulo_id>', methods=['POST'])
@seguridad.requiere_modulo('inventarios', 'registrar')
def cambiar_minimo(articulo_id):
    try:
        minimo = float(request.form.get('nivel_minimo', ''))
    except ValueError:
        flash('El nivel mínimo debe ser un número.', 'error')
        return redirect(url_for('inventarios.inicio') + '#minimos')
    if minimo < 0:
        flash('El nivel mínimo no puede ser negativo.', 'error')
        return redirect(url_for('inventarios.inicio') + '#minimos')
    articulo = db.consultar_uno('SELECT nombre FROM articulos WHERE id = %s', (articulo_id,))
    db.ejecutar('UPDATE articulos SET nivel_minimo = %s WHERE id = %s', (minimo, articulo_id))
    seguridad.registrar_bitacora('Cambió el nivel mínimo de ' + articulo['nombre'] + ' a ' + logica.formato_numero(minimo), 'articulos')
    flash('Nivel mínimo de ' + articulo['nombre'] + ' actualizado.', 'ok')
    return redirect(url_for('inventarios.inicio') + '#minimos')


@bp.route('/solicitud', methods=['POST'])
@seguridad.requiere_modulo('inventarios', 'registrar')
def solicitar():
    articulo_id = request.form.get('articulo_id', '')
    try:
        cantidad = float(request.form.get('cantidad', ''))
    except ValueError:
        flash('Escribe la cantidad a solicitar.', 'error')
        return redirect(url_for('inventarios.inicio') + '#minimos')
    if cantidad <= 0:
        flash('La cantidad debe ser mayor a cero.', 'error')
        return redirect(url_for('inventarios.inicio') + '#minimos')
    articulo = db.consultar_uno('SELECT nombre, unidad, tipo FROM articulos WHERE id = %s', (articulo_id,))
    if articulo is None or articulo['tipo'] == 'Producto terminado':
        flash('Solo se reabastecen materias primas y materiales de empaque.', 'error')
        return redirect(url_for('inventarios.inicio') + '#minimos')
    nuevo = db.ejecutar("INSERT INTO solicitudes_reabastecimiento (articulo_id, cantidad, fecha, estado, usuario_id) VALUES (%s, %s, %s, 'Pendiente', %s)",
                        (articulo_id, cantidad, db.hoy(), session['usuario_id']))
    seguridad.registrar_bitacora('Solicitó reabastecimiento ' + seguridad.folio('SOL', nuevo) + ' de ' + articulo['nombre'], 'solicitudes_reabastecimiento')
    flash('Solicitud ' + seguridad.folio('SOL', nuevo) + ' creada: ' + logica.formato_numero(cantidad) + ' ' + articulo['unidad'] + ' de ' + articulo['nombre'] + '.', 'ok')
    return redirect(url_for('inventarios.inicio') + '#solicitudes')
