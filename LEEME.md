# Prototipo SCM – Grupo Herdez (línea de enlatados)

Aplicaciones Empresariales · ITSR · Equipo: Yuliana Ferretiz Meza, Ana Cristina Infante Pérez, Perla Viviana Toledo López, Sandra Paola Torres Carbajal

## Qué necesitas
- **Python 3.10 o más nuevo.** Al instalarlo en Windows, marca la casilla **"Add Python to PATH"**.
- **MySQL (opcional).** Puede ser el de XAMPP. Si MySQL no está prendido, el sistema usa SQLite solito y funciona igual.
- Internet solo la primera vez (para instalar Flask y PyMySQL).

## Cómo arrancarlo
**Windows:** doble clic en `iniciar_windows.bat`. Instala lo necesario, levanta el sistema y abre el navegador en http://localhost:5000.

**Desde VS Code:** abre `app.py` y dale ▶.

La primera vez crea la base de datos `herdez_scm` con datos de prueba. En la ventana negra dice si está usando **MySQL** o **SQLite**.

### Si tu MySQL tiene contraseña
Abre `config.py` y pon la contraseña en `MYSQL_CONTRASENA`. En XAMPP normalmente va vacía.

### Dejar los datos como al inicio
Dale ▶ a `crear_bd.py` (o doble clic en `reiniciar_datos_windows.bat`). Hazlo antes de cada ensayo y antes de la expo.

## Usuarios (contraseña de todos: `herdez123`)
| Rol | Usuario |
|---|---|
| Administrador | sandra.torres@herdezscm.mx |
| Ventas | yuliana.ferretiz@herdezscm.mx |
| Compras | jorge.salinas@herdezscm.mx |
| Producción | perla.toledo@herdezscm.mx |
| Calidad | ana.infante@herdezscm.mx |
| Almacén (tableta) | daniel.hernandez@herdezscm.mx |
| Logística | fernanda.castillo@herdezscm.mx |
| Gerente | jose.ruiz@herdezscm.mx |
| (inactivo, para mostrar que no entra) | pedro.ramirez@herdezscm.mx |

5 intentos fallidos bloquean la cuenta 15 minutos; el admin la puede desbloquear.

## Estructura
```
app.py               arranque, login, panel, alertas
config.py            conexión y parámetros (días de caducidad, intentos)
db.py                acceso a datos (MySQL o SQLite)
seguridad.py         sesiones, permisos por rol, bitácora
logica.py            FEFO, verificación de materiales, alertas
crear_bd.py          crea las tablas y los datos de prueba
sql/esquema_mysql.sql  las 19 tablas
modulos/             un módulo (blueprint) por área:
  pedidos, inventarios, produccion, calidad,
  almacen, logistica, reportes, usuarios
templates/           pantallas HTML
static/              estilos y JavaScript
```

## Qué está programado y qué es propuesta
**Programado y funcionando:** login con roles y bloqueo; pedidos con disponibilidad y aviso a producción; inventario por lote con mínimos y caducidades; reabastecimiento; órdenes de producción con verificación de materiales y consumo FEFO; liberación/retención/rechazo de lotes por calidad; almacén en modo tableta (recepción, ubicación, surtido FEFO con escaneo); envíos y rastreo de lote; reportes con indicadores y exportación a Excel (CSV) y PDF (vista de impresión); usuarios, matriz de permisos y bitácora.

**Propuesta (no programado, se explica en la presentación):** nube, IA para pronósticos, sensores IoT, RPA y blockchain.
