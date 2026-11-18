from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import generate_password_hash
import db
import seguridad

bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')


@bp.route('/')
@seguridad.requiere_modulo('usuarios')
def inicio():
    usuarios = db.consultar('SELECT u.*, s.nombre AS sede FROM usuarios u LEFT JOIN sedes s ON s.id = u.sede_id ORDER BY u.activo DESC, u.nombre')
    for u in usuarios:
        u['bloqueado'] = bool(u['bloqueado_hasta']) and u['bloqueado_hasta'] > db.ahora()
    sedes = db.consultar('SELECT * FROM sedes ORDER BY id')
    rol_elegido = request.args.get('rol', 'almacen')
    if rol_elegido not in seguridad.NOMBRES_ROL:
        rol_elegido = 'almacen'
    permisos = seguridad.permisos_del_rol(rol_elegido)
    bitacora = db.consultar('SELECT b.*, u.nombre FROM bitacora b LEFT JOIN usuarios u ON u.id = b.usuario_id ORDER BY b.fecha_hora DESC, b.id DESC LIMIT 40')
    return render_template('usuarios/inicio.html', usuarios=usuarios, sedes=sedes, roles=seguridad.NOMBRES_ROL,
                           modulos=seguridad.MODULOS, rol_elegido=rol_elegido, permisos=permisos, bitacora=bitacora)


@bp.route('/nuevo', methods=['POST'])
@seguridad.requiere_modulo('usuarios', 'registrar')
def nuevo():
    nombre = request.form.get('nombre', '').strip()
    correo = request.form.get('correo', '').strip().lower()
    rol = request.form.get('rol', '')
    sede_id = request.form.get('sede_id', '')
    contrasena = request.form.get('contrasena', '')
    if nombre == '' or correo == '' or rol not in seguridad.NOMBRES_ROL or sede_id == '':
        flash('Llena nombre, correo, rol y sede.', 'error')
        return redirect(url_for('usuarios.inicio'))
    if len(contrasena) < 6:
        flash('La contraseña inicial debe tener al menos 6 caracteres.', 'error')
        return redirect(url_for('usuarios.inicio'))
    if db.consultar_uno('SELECT id FROM usuarios WHERE correo = %s', (correo,)) is not None:
        flash('Ya existe un usuario con ese correo.', 'error')
        return redirect(url_for('usuarios.inicio'))
    db.ejecutar('INSERT INTO usuarios (nombre, correo, contrasena, rol, sede_id, activo, intentos_fallidos) VALUES (%s, %s, %s, %s, %s, 1, 0)',
                (nombre, correo, generate_password_hash(contrasena, method='pbkdf2:sha256'), rol, sede_id))
    seguridad.registrar_bitacora('Creó el usuario ' + correo + ' con rol ' + rol, 'usuarios')
    flash('Usuario ' + correo + ' creado.', 'ok')
    return redirect(url_for('usuarios.inicio'))


@bp.route('/<int:usuario_id>', methods=['GET', 'POST'])
@seguridad.requiere_modulo('usuarios')
def editar(usuario_id):
    persona = db.consultar_uno('SELECT * FROM usuarios WHERE id = %s', (usuario_id,))
    if persona is None:
        abort(404)
    if request.method == 'POST':
        if not seguridad.puede('usuarios', 'registrar'):
            abort(403)
        nombre = request.form.get('nombre', '').strip()
        rol = request.form.get('rol', '')
        sede_id = request.form.get('sede_id', '')
        contrasena = request.form.get('contrasena', '')
        if nombre == '' or rol not in seguridad.NOMBRES_ROL:
            flash('Revisa el nombre y el rol.', 'error')
            return redirect(url_for('usuarios.editar', usuario_id=usuario_id))
        if usuario_id == session['usuario_id'] and rol != 'admin':
            flash('No puedes quitarte a ti mismo el rol de administrador.', 'error')
            return redirect(url_for('usuarios.editar', usuario_id=usuario_id))
        db.ejecutar('UPDATE usuarios SET nombre = %s, rol = %s, sede_id = %s WHERE id = %s', (nombre, rol, sede_id, usuario_id))
        if contrasena != '':
            if len(contrasena) < 6:
                flash('La contraseña debe tener al menos 6 caracteres.', 'error')
                return redirect(url_for('usuarios.editar', usuario_id=usuario_id))
            db.ejecutar('UPDATE usuarios SET contrasena = %s WHERE id = %s', (generate_password_hash(contrasena, method='pbkdf2:sha256'), usuario_id))
        seguridad.registrar_bitacora('Modificó el usuario ' + persona['correo'], 'usuarios')
        flash('Usuario actualizado.', 'ok')
        return redirect(url_for('usuarios.inicio'))
    sedes = db.consultar('SELECT * FROM sedes ORDER BY id')
    return render_template('usuarios/editar.html', persona=persona, sedes=sedes, roles=seguridad.NOMBRES_ROL)


@bp.route('/<int:usuario_id>/activo', methods=['POST'])
@seguridad.requiere_modulo('usuarios', 'registrar')
def cambiar_activo(usuario_id):
    persona = db.consultar_uno('SELECT * FROM usuarios WHERE id = %s', (usuario_id,))
    if persona is None:
        abort(404)
    if usuario_id == session['usuario_id']:
        flash('No puedes desactivar tu propia cuenta.', 'error')
        return redirect(url_for('usuarios.inicio'))
    nuevo = 0 if persona['activo'] == 1 else 1
    db.ejecutar('UPDATE usuarios SET activo = %s WHERE id = %s', (nuevo, usuario_id))
    accion = 'Activó' if nuevo == 1 else 'Desactivó'
    seguridad.registrar_bitacora(accion + ' el usuario ' + persona['correo'], 'usuarios')
    flash(accion + ' a ' + persona['nombre'] + '.', 'ok')
    return redirect(url_for('usuarios.inicio'))


@bp.route('/<int:usuario_id>/desbloquear', methods=['POST'])
@seguridad.requiere_modulo('usuarios', 'registrar')
def desbloquear(usuario_id):
    persona = db.consultar_uno('SELECT * FROM usuarios WHERE id = %s', (usuario_id,))
    if persona is None:
        abort(404)
    db.ejecutar('UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = %s', (usuario_id,))
    seguridad.registrar_bitacora('Desbloqueó el usuario ' + persona['correo'], 'usuarios')
    flash('Cuenta de ' + persona['nombre'] + ' desbloqueada.', 'ok')
    return redirect(url_for('usuarios.inicio'))


@bp.route('/permisos', methods=['POST'])
@seguridad.requiere_modulo('usuarios', 'registrar')
def guardar_permisos():
    rol = request.form.get('rol', '')
    if rol not in seguridad.NOMBRES_ROL:
        abort(400)
    for modulo in seguridad.MODULOS:
        clave = modulo['clave']
        consultar = 1 if request.form.get('c_' + clave) else 0
        registrar = 1 if request.form.get('r_' + clave) else 0
        if registrar == 1:
            consultar = 1
        if rol == 'admin' and clave == 'usuarios':
            consultar = 1
            registrar = 1
        existe = db.consultar_uno('SELECT id FROM roles_permisos WHERE rol = %s AND modulo = %s', (rol, clave))
        if existe is None:
            db.ejecutar('INSERT INTO roles_permisos (rol, modulo, puede_consultar, puede_registrar) VALUES (%s, %s, %s, %s)',
                        (rol, clave, consultar, registrar))
        else:
            db.ejecutar('UPDATE roles_permisos SET puede_consultar = %s, puede_registrar = %s WHERE id = %s', (consultar, registrar, existe['id']))
    seguridad.registrar_bitacora('Cambió los permisos del rol ' + rol, 'roles_permisos')
    flash('Permisos de ' + seguridad.NOMBRES_ROL[rol] + ' guardados.', 'ok')
    return redirect(url_for('usuarios.inicio', rol=rol) + '#permisos')
