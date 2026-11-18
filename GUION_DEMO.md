# Guion de la demo (unos 6–8 minutos)

## Antes de empezar (en casa o 10 min antes)
1. Si usan MySQL: abrir XAMPP y darle **Start** a MySQL. Si no, no pasa nada (usa SQLite).
2. Doble clic en `reiniciar_datos_windows.bat` para dejar los datos limpios.
3. Doble clic en `iniciar_windows.bat` y esperar a que abra el navegador.
4. Poner el zoom del navegador en 110–125 % para que se vea en el proyector.
5. Dejar la ventana negra abierta (si la cierran, se apaga el sistema).

Tip: tengan abierta una pestaña de incógnito para cambiar de usuario rápido, o usen **Salir** arriba a la derecha.

## La historia que van a contar
Supermercados del Centro (Querétaro) pide rajas y puré. No alcanzan las rajas, producción fabrica lo que falta, calidad libera el lote, almacén surte con FEFO, logística entrega y el gerente ve los indicadores. Todo queda en la bitácora.

---

### 1. Ventas – `yuliana.ferretiz@herdezscm.mx`
- En el panel se ven las alertas del día.
- **Pedidos → Nuevo pedido.** Cliente: **Supermercados del Centro**.
  - Renglón 1: **Rajas de jalapeño 380 g × 200** → el sistema muestra que solo hay 170 disponibles.
  - Renglón 2: **Puré de tomate 210 g × 20**.
- Guardar. Se crea **PED-0008** y, como faltan 30 cajas de rajas, **se avisa a producción automáticamente**.
- Qué decir: "ventas ya no tiene que llamar a planta para saber si hay producto".

### 2. Producción – `perla.toledo@herdezscm.mx`
- En el panel aparece el **aviso del pedido PED-0008**.
- Mostrar la orden **OP-0009 (chipotles)**: dice **"Faltan materiales"** y no deja iniciarla. → "el sistema no deja arrancar algo que no se puede terminar".
- Crear una orden nueva de **Rajas de jalapeño 380 g, 30 cajas** → **Verificar materiales** (todo alcanza) → crear → **Iniciar** → **Registrar producción: 30**.
- Se descuentan los materiales por FEFO y se crea un lote nuevo en estado **Pendiente**.

### 3. Calidad – `ana.infante@herdezscm.mx`
- Ver los lotes pendientes de inspección.
- **Liberar** el lote nuevo de rajas.
- Comentar que retener o rechazar pide observaciones obligatorias.

### 4. Almacén (tableta) – `daniel.hernandez@herdezscm.mx`
- Pestaña **Ubicación**: asignarle ubicación al lote recién liberado.
- Pestaña **Surtido** → abrir **PED-0008**. El sistema dice qué lote tomar primero (**FEFO: el que caduca antes**).
- Truco para lucirse: en el puré, escanear/escribir el número del **lote retenido** → el sistema lo **rechaza**. Luego confirmar el lote correcto.
- Confirmar todos los lotes → **Registrar salida**. El pedido pasa a **Surtido**.

### 5. Logística – `fernanda.castillo@herdezscm.mx`
- Crear envío para **PED-0008** en **Ruta Centro** con destino **Querétaro**.
- **En tránsito** → el pedido pasa a Enviado. **Entregado** → el pedido pasa a Entregado.
- **Rastreo de lote:** buscar el lote de rajas y mostrar a qué pedidos, clientes y destinos se fue. → "si hubiera un problema con un lote, sabemos en minutos a quién avisarle".

### 6. Gerente – `jose.ruiz@herdezscm.mx`
- **Reportes:** los 4 indicadores con su semáforo (entregas a tiempo, rotación, % rechazado, lotes por caducar) y el tiempo de entrega por destino.
- **Exportar a Excel** y mostrar la vista para **PDF**.

### 7. Administrador – `sandra.torres@herdezscm.mx`
- **Usuarios:** mostrar la matriz de permisos por rol.
- **Bitácora:** se ve todo lo que acaban de hacer, con usuario, fecha y hora.
- Opcional: intentar entrar con `pedro.ramirez@herdezscm.mx` (inactivo) y ver que no deja.

---

## Si el profe pregunta…
- **¿Con qué está hecho?** Python con Flask, MySQL (con SQLite de respaldo), HTML/CSS/JS. Cada área es un módulo separado.
- **¿Qué es FEFO?** *First Expired, First Out*: sale primero lo que caduca antes, para no tirar producto.
- **¿Cómo se controla quién hace qué?** Cada rol tiene permisos guardados en la base de datos; si alguien entra a una pantalla que no le toca, sale error 403. Todo queda en la bitácora.
- **¿Las contraseñas?** Se guardan cifradas (hash), nunca en texto. Después de 5 intentos fallidos se bloquea la cuenta 15 minutos.
- **¿Y la nube, IA, IoT…?** Son la propuesta de evolución del sistema; el prototipo cubre los procesos principales de punta a punta.
- **¿Por qué tableta en almacén?** Porque el almacenista está de pie y en movimiento; botones grandes y escaneo de lote.

## Si algo falla
- **No abre el navegador:** entrar a mano a http://localhost:5000
- **"python no se reconoce":** reinstalar Python marcando "Add Python to PATH".
- **Los datos quedaron raros por un ensayo:** cerrar la ventana negra, correr `reiniciar_datos_windows.bat` y volver a iniciar.
