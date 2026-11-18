from functools import wraps
from flask import session, redirect, url_for, flash, abort, current_app
import db

NOMBRES_ROL = {
    'ventas': 'Ejecutivo de Ventas y Comercialización',
    'compras': 'Encargado de Abastecimiento y Compras',
    'produccion': 'Jefe de Producción',
    'calidad': 'Responsable de Control de Calidad',
    'almacen': 'Encargado de Almacén e Inventarios',
    'logistica': 'Coordinador de Logística y Distribución',
    'gerente': 'Gerente de Cadena de Suministro',
    'admin': 'Administrador del sistema (TI)',
}

MODULOS = [
    {'clave': 'pedidos', 'nombre': 'Pedidos', 'ruta': 'pedidos.inicio'},
    {'clave': 'inventarios', 'nombre': 'Inventarios', 'ruta': 'inventarios.inicio'},
    {'clave': 'produccion', 'nombre': 'Producción', 'ruta': 'produccion.inicio'},
    {'clave': 'calidad', 'nombre': 'Calidad', 'ruta': 'calidad.inicio'},
    {'clave': 'almacen', 'nombre': 'Almacén', 'ruta': 'almacen.surtido'},
    {'clave': 'logistica', 'nombre': 'Logística', 'ruta': 'logistica.inicio'},
    {'clave': 'reportes', 'nombre': 'Reportes', 'ruta': 'reportes.inicio'},
    {'clave': 'usuarios', 'nombre': 'Usuarios y permisos', 'ruta': 'usuarios.inicio'},
]


def permisos_del_rol(rol):
    filas = db.consultar('SELECT modulo, puede_consultar, puede_registrar FROM roles_permisos WHERE rol = %s', (rol,))
    permisos = {}
    for fila in filas:
        permisos[fila['modulo']] = {'consultar': fila['puede_consultar'] == 1, 'registrar': fila['puede_registrar'] == 1}
    return permisos


def usuario_actual():
    if 'usuario_id' not in session:
        return None
    return {'id': session['usuario_id'], 'nombre': session['nombre'], 'rol': session['rol']}


def puede(modulo, accion='consultar'):
    if 'rol' not in session:
        return False
    permisos = permisos_del_rol(session['rol'])
    if modulo not in permisos:
        return False
    return permisos[modulo][accion]


def menu_del_usuario():
    if 'rol' not in session:
        return []
    permisos = permisos_del_rol(session['rol'])
    menu = []
    for modulo in MODULOS:
        if modulo['clave'] not in current_app.blueprints:
            continue
        if modulo['clave'] in permisos and permisos[modulo['clave']]['consultar']:
            menu.append(modulo)
    return menu


def requiere_sesion(funcion):
    @wraps(funcion)
    def envoltura(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Inicia sesión para continuar.', 'aviso')
            return redirect(url_for('login'))
        return funcion(*args, **kwargs)
    return envoltura


def requiere_modulo(modulo, accion='consultar'):
    def decorador(funcion):
        @wraps(funcion)
        def envoltura(*args, **kwargs):
            if 'usuario_id' not in session:
                flash('Inicia sesión para continuar.', 'aviso')
                return redirect(url_for('login'))
            if not puede(modulo, accion):
                abort(403)
            return funcion(*args, **kwargs)
        return envoltura
    return decorador


def registrar_bitacora(operacion, tabla):
    usuario_id = session.get('usuario_id')
    db.ejecutar('INSERT INTO bitacora (usuario_id, operacion, tabla_afectada, fecha_hora) VALUES (%s, %s, %s, %s)',
                (usuario_id, operacion, tabla, db.ahora()))


def folio(prefijo, numero):
    return prefijo + '-' + str(numero).zfill(4)
