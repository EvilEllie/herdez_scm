import db
import config


def existencia_disponible(articulo_id):
    fila = db.consultar_uno(
        "SELECT COALESCE(SUM(cantidad), 0) AS total FROM lotes "
        "WHERE articulo_id = %s AND estado_calidad = 'Liberado' AND cantidad > 0 AND fecha_caducidad > %s",
        (articulo_id, db.hoy()))
    return float(fila['total'])


def lotes_fefo(articulo_id):
    return db.consultar(
        "SELECT l.*, a.nombre AS articulo, a.unidad FROM lotes l JOIN articulos a ON a.id = l.articulo_id "
        "WHERE l.articulo_id = %s AND l.estado_calidad = 'Liberado' AND l.cantidad > 0 AND l.fecha_caducidad > %s "
        "ORDER BY l.fecha_caducidad, l.id",
        (articulo_id, db.hoy()))


def asignar_fefo(articulo_id, cantidad):
    asignaciones = []
    pendiente = float(cantidad)
    for lote in lotes_fefo(articulo_id):
        if pendiente <= 0:
            break
        tomar = min(pendiente, float(lote['cantidad']))
        asignaciones.append({'lote': lote, 'cantidad': tomar})
        pendiente = pendiente - tomar
    return asignaciones, max(pendiente, 0)


def verificar_materiales(producto_id, cajas):
    receta = db.consultar(
        "SELECT r.material_id, r.cantidad_por_caja, a.nombre, a.unidad, a.codigo FROM recetas r "
        "JOIN articulos a ON a.id = r.material_id WHERE r.producto_id = %s ORDER BY a.codigo",
        (producto_id,))
    resultado = []
    for renglon in receta:
        necesario = round(float(renglon['cantidad_por_caja']) * float(cajas), 2)
        disponible = existencia_disponible(renglon['material_id'])
        resultado.append({
            'material_id': renglon['material_id'],
            'codigo': renglon['codigo'],
            'nombre': renglon['nombre'],
            'unidad': renglon['unidad'],
            'necesario': necesario,
            'disponible': disponible,
            'alcanza': disponible >= necesario,
            'faltante': max(round(necesario - disponible, 2), 0),
        })
    return resultado


def todo_alcanza(verificacion):
    for renglon in verificacion:
        if not renglon['alcanza']:
            return False
    return True


def estado_lote(lote, existencia_total, nivel_minimo):
    if lote['estado_calidad'] in ('Retenido', 'Rechazado'):
        return lote['estado_calidad']
    if lote['estado_calidad'] == 'Pendiente':
        return 'Pendiente de inspección'
    if lote['fecha_caducidad'] <= db.hoy():
        return 'Caducado'
    dias = config.DIAS_POR_CADUCAR_MP if lote.get('tipo') == 'Materia prima' else config.DIAS_POR_CADUCAR
    if lote['fecha_caducidad'] <= db.sumar_dias(db.hoy(), dias):
        return 'Por caducar'
    if existencia_total <= float(nivel_minimo):
        return 'Bajo el mínimo'
    return 'Normal'


def articulos_bajo_minimo():
    articulos = db.consultar('SELECT * FROM articulos ORDER BY codigo')
    lista = []
    for articulo in articulos:
        total = existencia_disponible(articulo['id'])
        if total <= float(articulo['nivel_minimo']):
            articulo['existencia'] = total
            lista.append(articulo)
    return lista


def lotes_por_caducar():
    return db.consultar(
        "SELECT l.*, a.nombre AS articulo, a.unidad, a.tipo FROM lotes l JOIN articulos a ON a.id = l.articulo_id "
        "WHERE l.cantidad > 0 AND l.estado_calidad = 'Liberado' AND l.fecha_caducidad > %s AND "
        "((a.tipo = 'Materia prima' AND l.fecha_caducidad <= %s) OR (a.tipo <> 'Materia prima' AND l.fecha_caducidad <= %s)) "
        "ORDER BY l.fecha_caducidad",
        (db.hoy(), db.sumar_dias(db.hoy(), config.DIAS_POR_CADUCAR_MP), db.sumar_dias(db.hoy(), config.DIAS_POR_CADUCAR)))


def formato_numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return valor
    if numero == int(numero):
        return '{:,.0f}'.format(numero)
    return '{:,.2f}'.format(numero).rstrip('0').rstrip('.')


def formato_fecha(texto):
    if not texto:
        return '—'
    partes = str(texto)[:10].split('-')
    if len(partes) != 3:
        return texto
    return partes[2] + '/' + partes[1] + '/' + partes[0]
