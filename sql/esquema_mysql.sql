CREATE TABLE roles_permisos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  rol VARCHAR(30) NOT NULL,
  modulo VARCHAR(30) NOT NULL,
  puede_consultar INT NOT NULL DEFAULT 0,
  puede_registrar INT NOT NULL DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE sedes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL,
  tipo VARCHAR(30) NOT NULL,
  direccion VARCHAR(150)
) ENGINE=InnoDB;

CREATE TABLE usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL,
  correo VARCHAR(80) NOT NULL UNIQUE,
  contrasena VARCHAR(255) NOT NULL,
  rol VARCHAR(30) NOT NULL,
  sede_id INT,
  activo INT NOT NULL DEFAULT 1,
  intentos_fallidos INT NOT NULL DEFAULT 0,
  bloqueado_hasta DATETIME NULL,
  FOREIGN KEY (sede_id) REFERENCES sedes(id)
) ENGINE=InnoDB;

CREATE TABLE bitacora (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT,
  operacion VARCHAR(200) NOT NULL,
  tabla_afectada VARCHAR(40),
  fecha_hora DATETIME NOT NULL,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB;

CREATE TABLE articulos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(20) NOT NULL UNIQUE,
  nombre VARCHAR(80) NOT NULL,
  tipo VARCHAR(30) NOT NULL,
  unidad VARCHAR(20) NOT NULL,
  vida_util_dias INT NOT NULL DEFAULT 365,
  nivel_minimo DECIMAL(12,2) NOT NULL DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE proveedores (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL,
  contacto VARCHAR(80),
  telefono VARCHAR(20),
  materiales VARCHAR(150)
) ENGINE=InnoDB;

CREATE TABLE clientes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL,
  tipo VARCHAR(40),
  direccion VARCHAR(150),
  contacto VARCHAR(80)
) ENGINE=InnoDB;

CREATE TABLE recetas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  producto_id INT NOT NULL,
  material_id INT NOT NULL,
  cantidad_por_caja DECIMAL(12,3) NOT NULL,
  FOREIGN KEY (producto_id) REFERENCES articulos(id),
  FOREIGN KEY (material_id) REFERENCES articulos(id)
) ENGINE=InnoDB;

CREATE TABLE pedidos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cliente_id INT NOT NULL,
  fecha_registro DATE NOT NULL,
  fecha_requerida DATE NOT NULL,
  estado VARCHAR(30) NOT NULL,
  usuario_id INT,
  FOREIGN KEY (cliente_id) REFERENCES clientes(id),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB;

CREATE TABLE detalle_pedido (
  id INT AUTO_INCREMENT PRIMARY KEY,
  pedido_id INT NOT NULL,
  articulo_id INT NOT NULL,
  cantidad DECIMAL(12,2) NOT NULL,
  FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
  FOREIGN KEY (articulo_id) REFERENCES articulos(id)
) ENGINE=InnoDB;

CREATE TABLE ordenes_produccion (
  id INT AUTO_INCREMENT PRIMARY KEY,
  articulo_id INT NOT NULL,
  cantidad_planeada DECIMAL(12,2) NOT NULL,
  cantidad_producida DECIMAL(12,2) NOT NULL DEFAULT 0,
  pedido_id INT NULL,
  fecha_programada DATE NOT NULL,
  fecha_termino DATE NULL,
  estado VARCHAR(30) NOT NULL,
  usuario_id INT,
  FOREIGN KEY (articulo_id) REFERENCES articulos(id),
  FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB;

CREATE TABLE lotes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  numero_lote VARCHAR(30) NOT NULL UNIQUE,
  articulo_id INT NOT NULL,
  sede_id INT NOT NULL,
  ubicacion VARCHAR(30) NOT NULL,
  cantidad DECIMAL(12,2) NOT NULL,
  fecha_entrada DATE NOT NULL,
  fecha_caducidad DATE NOT NULL,
  estado_calidad VARCHAR(20) NOT NULL,
  proveedor_id INT NULL,
  orden_id INT NULL,
  FOREIGN KEY (articulo_id) REFERENCES articulos(id),
  FOREIGN KEY (sede_id) REFERENCES sedes(id),
  FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),
  FOREIGN KEY (orden_id) REFERENCES ordenes_produccion(id)
) ENGINE=InnoDB;

CREATE TABLE movimientos_almacen (
  id INT AUTO_INCREMENT PRIMARY KEY,
  tipo VARCHAR(20) NOT NULL,
  lote_id INT NOT NULL,
  cantidad DECIMAL(12,2) NOT NULL,
  fecha DATE NOT NULL,
  usuario_id INT,
  pedido_id INT NULL,
  FOREIGN KEY (lote_id) REFERENCES lotes(id),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
) ENGINE=InnoDB;

CREATE TABLE consumos_produccion (
  id INT AUTO_INCREMENT PRIMARY KEY,
  orden_id INT NOT NULL,
  lote_id INT NOT NULL,
  cantidad DECIMAL(12,2) NOT NULL,
  FOREIGN KEY (orden_id) REFERENCES ordenes_produccion(id),
  FOREIGN KEY (lote_id) REFERENCES lotes(id)
) ENGINE=InnoDB;

CREATE TABLE inspecciones_calidad (
  id INT AUTO_INCREMENT PRIMARY KEY,
  lote_id INT NOT NULL,
  resultado VARCHAR(20) NOT NULL,
  observaciones VARCHAR(250),
  fecha DATE NOT NULL,
  usuario_id INT,
  FOREIGN KEY (lote_id) REFERENCES lotes(id),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB;

CREATE TABLE solicitudes_reabastecimiento (
  id INT AUTO_INCREMENT PRIMARY KEY,
  articulo_id INT NOT NULL,
  cantidad DECIMAL(12,2) NOT NULL,
  fecha DATE NOT NULL,
  estado VARCHAR(20) NOT NULL,
  usuario_id INT,
  FOREIGN KEY (articulo_id) REFERENCES articulos(id),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB;

CREATE TABLE rutas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(60) NOT NULL,
  sede_origen_id INT NOT NULL,
  destinos VARCHAR(150),
  FOREIGN KEY (sede_origen_id) REFERENCES sedes(id)
) ENGINE=InnoDB;

CREATE TABLE envios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  pedido_id INT NOT NULL,
  ruta_id INT NOT NULL,
  destino VARCHAR(100) NOT NULL,
  fecha_salida DATE NOT NULL,
  fecha_entrega DATE NULL,
  estado VARCHAR(20) NOT NULL,
  FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
  FOREIGN KEY (ruta_id) REFERENCES rutas(id)
) ENGINE=InnoDB;

CREATE TABLE avisos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  tipo VARCHAR(40) NOT NULL,
  mensaje VARCHAR(250) NOT NULL,
  rol_destino VARCHAR(30) NOT NULL,
  fecha DATE NOT NULL,
  estado VARCHAR(20) NOT NULL,
  pedido_id INT NULL,
  FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
) ENGINE=InnoDB;
