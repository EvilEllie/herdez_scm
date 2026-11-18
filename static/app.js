
function agregarRenglon() {
  var tabla = document.getElementById('tabla-productos');
  var renglones = tabla.getElementsByClassName('renglon-producto');
  var nuevo = renglones[0].cloneNode(true);
  nuevo.getElementsByTagName('select')[0].value = '';
  nuevo.getElementsByTagName('input')[0].value = '';
  nuevo.getElementsByClassName('celda-disponible')[0].innerHTML = '<span class="etiqueta gris">Sin seleccionar</span>';
  tabla.getElementsByTagName('tbody')[0].appendChild(nuevo);
}

function actualizarDisponible(elemento) {
  var renglon = elemento.closest('tr');
  var producto = renglon.getElementsByTagName('select')[0].value;
  var cantidad = parseFloat(renglon.getElementsByTagName('input')[0].value);
  var celda = renglon.getElementsByClassName('celda-disponible')[0];
  if (producto === '') {
    celda.innerHTML = '<span class="etiqueta gris">Sin seleccionar</span>';
    return;
  }
  var disponible = disponibles[producto];
  if (isNaN(cantidad) || cantidad <= 0) {
    celda.innerHTML = '<span class="etiqueta gris">' + disponible.toLocaleString('es-MX') + ' cajas disponibles</span>';
    return;
  }
  if (disponible >= cantidad) {
    celda.innerHTML = '<span class="etiqueta verde">Hay existencia (' + disponible.toLocaleString('es-MX') + ')</span>';
  } else {
    var falta = cantidad - disponible;
    celda.innerHTML = '<span class="etiqueta roja">Faltan ' + falta.toLocaleString('es-MX') + ' cajas</span>';
  }
}

function confirmar(mensaje) {
  return window.confirm(mensaje);
}
