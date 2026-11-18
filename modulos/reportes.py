import csv
import io
from flask import Blueprint, render_template, request, Response
import db
import logica
import seguridad

bp = Blueprint('reportes', __name__, url_prefix='/reportes')


def nivel(valor, optimo, precaucion, mayor_es_mejor=True):
    if mayor_es_mejor:
        if valor >= optimo:
            return 'Óptimo'
        if valor >= precaucion:
            return 'Precaución'
        return 'Crítico'
    if valor <= optimo:
        return 'Óptimo'
    if valor <= precaucion:
        return 'Precaución'
    return 'Crítico'


def calcular(desde, hasta):
    entregados = db.consultar("SELECT e.*, p.fecha_requerida, c.nombre AS cliente FROM envios e JOIN pedidos p ON p.id = e.pedido_id "
                              "JOIN clientes c ON c.id = p.cliente_id WHERE e.estado = 'Entregado' AND e.fecha_entrega >= %s AND e.fecha_entrega <= %s",
                              (desde, hasta))
    a_tiempo = 0
    for e in entregados:
        if e['fecha_entrega'] <= e['fecha_requerida']:
            a_tiempo = a_tiempo + 1
    porcentaje_tiempo = round(a_tiempo * 100.0 / len(entregados), 1) if len(entregados) > 0 else 0

    salidas = db.consultar_uno("SELECT COALESCE(SUM(m.cantidad), 0) AS total FROM movimientos_almacen m JOIN lotes l ON l.id = m.lote_id "
                               "JOIN articulos a ON a.id = l.articulo_id WHERE m.tipo = 'Salida' AND a.tipo = 'Producto terminado' "
                               "AND m.fecha >= %s AND m.fecha <= %s", (desde, hasta))
    existencia = db.consultar_uno("SELECT COALESCE(SUM(l.cantidad), 0) AS total FROM lotes l JOIN articulos a ON a.id = l.articulo_id "
                                  "WHERE a.tipo = 'Producto terminado' AND l.estado_calidad = 'Liberado'")
    rotacion = round(float(salidas['total']) / float(existencia['total']), 2) if float(existencia['total']) > 0 else 0

    inspecciones = db.consultar('SELECT resultado FROM inspecciones_calidad WHERE fecha >= %s AND fecha <= %s', (desde, hasta))
    rechazados = 0
    for i in inspecciones:
        if i['resultado'] == 'Rechazado':
            rechazados = rechazados + 1
    porcentaje_rechazo = round(rechazados * 100.0 / len(inspecciones), 1) if len(inspecciones) > 0 else 0

    por_caducar = logica.lotes_por_caducar()

    indicadores = [
        {'nombre': 'Pedidos entregados completos y a tiempo', 'valor': logica.formato_numero(porcentaje_tiempo) + ' %',
         'detalle': str(a_tiempo) + ' de ' + str(len(entregados)) + ' entregas', 'barra': porcentaje_tiempo,
         'nivel': nivel(porcentaje_tiempo, 90, 75)},
        {'nombre': 'Rotación de inventario (producto terminado)', 'valor': logica.formato_numero(rotacion) + ' veces',
         'detalle': logica.formato_numero(salidas['total']) + ' cajas surtidas / ' + logica.formato_numero(existencia['total']) + ' en existencia',
         'barra': min(rotacion * 100, 100), 'nivel': nivel(rotacion, 1, 0.5)},
        {'nombre': 'Lotes rechazados por calidad', 'valor': logica.formato_numero(porcentaje_rechazo) + ' %',
         'detalle': str(rechazados) + ' de ' + str(len(inspecciones)) + ' inspecciones', 'barra': porcentaje_rechazo,
         'nivel': nivel(porcentaje_rechazo, 10, 20, False)},
        {'nombre': 'Lotes por caducar', 'valor': str(len(por_caducar)) + (' lote' if len(por_caducar) == 1 else ' lotes'),
         'detalle': 'Producto y empaque: 30 días · materia prima: 5 días', 'barra': min(len(por_caducar) * 20, 100),
         'nivel': nivel(len(por_caducar), 0, 2, False)},
    ]

    destinos = {}
    for e in entregados:
        dias = db.dias_entre(e['fecha_salida'], e['fecha_entrega'])
        if e['destino'] not in destinos:
            destinos[e['destino']] = []
        destinos[e['destino']].append(dias)
    tiempos = []
    mayor = 1
    for destino in destinos:
        promedio = round(sum(destinos[destino]) / float(len(destinos[destino])), 1)
        mayor = max(mayor, promedio)
        tiempos.append({'destino': destino, 'dias': promedio, 'entregas': len(destinos[destino])})
    for t in tiempos:
        t['ancho'] = round(t['dias'] * 100 / mayor)
    tiempos.sort(key=lambda t: t['dias'], reverse=True)

    estados = db.consultar('SELECT estado, COUNT(*) AS total FROM pedidos WHERE fecha_registro >= %s AND fecha_registro <= %s GROUP BY estado',
                           (desde, hasta))
    pedidos = db.consultar("SELECT p.*, c.nombre AS cliente, e.fecha_entrega FROM pedidos p JOIN clientes c ON c.id = p.cliente_id "
                           "LEFT JOIN envios e ON e.pedido_id = p.id WHERE p.fecha_registro >= %s AND p.fecha_registro <= %s ORDER BY p.id",
                           (desde, hasta))
    return indicadores, tiempos, estados, pedidos, por_caducar


def leer_periodo():
    hasta = request.args.get('hasta', '') or db.hoy()
    desde = request.args.get('desde', '') or db.sumar_dias(hasta, -45)
    if desde > hasta:
        desde, hasta = hasta, desde
    return desde, hasta


@bp.route('/')
@seguridad.requiere_modulo('reportes')
def inicio():
    desde, hasta = leer_periodo()
    indicadores, tiempos, estados, pedidos, por_caducar = calcular(desde, hasta)
    return render_template('reportes/inicio.html', desde=desde, hasta=hasta, indicadores=indicadores, tiempos=tiempos,
                           estados=estados, pedidos=pedidos, por_caducar=por_caducar, imprimir=request.args.get('imprimir') == '1')


@bp.route('/excel')
@seguridad.requiere_modulo('reportes')
def excel():
    desde, hasta = leer_periodo()
    indicadores, tiempos, estados, pedidos, por_caducar = calcular(desde, hasta)
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(['Reporte de la cadena de suministro - Herdez SCM'])
    escritor.writerow(['Periodo', logica.formato_fecha(desde), logica.formato_fecha(hasta)])
    escritor.writerow([])
    escritor.writerow(['Indicador', 'Valor', 'Detalle', 'Nivel'])
    for i in indicadores:
        escritor.writerow([i['nombre'], i['valor'], i['detalle'], i['nivel']])
    escritor.writerow([])
    escritor.writerow(['Destino', 'Días promedio de entrega', 'Entregas'])
    for t in tiempos:
        escritor.writerow([t['destino'], t['dias'], t['entregas']])
    escritor.writerow([])
    escritor.writerow(['Pedido', 'Cliente', 'Registro', 'Requerido', 'Entrega', 'Estado'])
    for p in pedidos:
        escritor.writerow([seguridad.folio('PED', p['id']), p['cliente'], logica.formato_fecha(p['fecha_registro']),
                           logica.formato_fecha(p['fecha_requerida']), logica.formato_fecha(p['fecha_entrega']), p['estado']])
    seguridad.registrar_bitacora('Descargó el reporte en Excel', 'reportes')
    contenido = '﻿' + salida.getvalue()
    nombre = 'reporte_scm_' + desde + '_a_' + hasta + '.csv'
    return Response(contenido, mimetype='text/csv; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename=' + nombre})
