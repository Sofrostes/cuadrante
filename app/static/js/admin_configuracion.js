(() => {
  const $ = (id) => document.getElementById(id);
  const resultado = $("resultado");
  const rutaNorm = $("ruta-normalizada");

  function pintaResultado(obj) {
    resultado.style.display = "block";
    resultado.className = "resultado " + (obj.ok ? "ok" : "error");
    let txt = (obj.mensaje || (obj.ok ? "OK" : "Error")) + "\n";
    if (obj.ruta_normalizada) txt += `Ruta: ${obj.ruta_normalizada}\n`;
    if (obj.ruta_completa)   txt += `Ruta completa: ${obj.ruta_completa}\n`;
    if (obj.hojas && obj.hojas.length) txt += `Hojas: ${obj.hojas.join(", ")}\n`;
    if (obj.celda_servicio_probada) txt += `Primer servicio: ${obj.celda_servicio_probada}\n`;
    if (obj.muestra && obj.muestra.length) txt += `Muestra: ${obj.muestra.join(" · ")}\n`;
    if (obj.detalle_error) txt += `Detalle: ${obj.detalle_error}\n`;
    resultado.textContent = txt;
  }

  function formData() {
    const fd = new FormData();
    fd.append("excel_ruta", $("excel_ruta").value);
    fd.append("excel_hoja", $("excel_hoja").value);
    fd.append("col_identificador", $("col_identificador").value);
    fd.append("col_nombre", $("col_nombre").value);
    fd.append("col_cf", $("col_cf").value);
    fd.append("fila_inicio_datos", $("fila_inicio_datos").value);
    fd.append("col_servicios", $("col_servicios").value);
    fd.append("gap", $("gap").value);
    return fd;
  }

  async function previewLayout() {
    const fd = new FormData();
    fd.append("col_inicio_servicios", $("col_servicios").value);
    fd.append("gap", $("gap").value);
    fd.append("fila_inicio_datos", $("fila_inicio_datos").value);
    fd.append("col_identificador", $("col_identificador").value);
    fd.append("col_nombre", $("col_nombre").value);
    fd.append("col_cf", $("col_cf").value);
    fd.append("n", "12");

    const r = await fetch("/admin/configuracion/preview-layout", { method: "POST", body: fd });
    const data = await r.json();
    if (!data.ok) {
      $("preview-columnas").textContent = "Servicios: " + (data.mensaje || "error");
      $("preview-celda").textContent = "";
      return;
    }
    $("preview-columnas").textContent = "Servicios: " + data.columnas.join(", ");
    $("preview-celda").textContent = "Primer servicio: " + data.primera_celda;
  }

  ["col_servicios", "gap", "fila_inicio_datos", "col_identificador", "col_nombre", "col_cf"]
    .forEach(id => $(id).addEventListener("input", previewLayout));

  $("excel_ruta").addEventListener("blur", () => {
    const v = $("excel_ruta").value.trim();
    rutaNorm.textContent = v || "—";
  });

  $("btn-cargar-hojas").addEventListener("click", async () => {
    const fd = new FormData();
    fd.append("excel_ruta", $("excel_ruta").value);
    const r = await fetch("/admin/configuracion/cargar-hojas", { method: "POST", body: fd });
    const data = await r.json();
    if (!data.ok) {
      pintaResultado({ ok: false, mensaje: data.mensaje });
      return;
    }
    const sel = $("excel_hoja");
    const actual = sel.value;
    sel.innerHTML = "";
    data.hojas.forEach(h => {
      const opt = document.createElement("option");
      opt.value = h; opt.textContent = h;
      if (h === actual) opt.selected = true;
      sel.appendChild(opt);
    });
    pintaResultado({ ok: true, mensaje: data.mensaje, hojas: data.hojas });
  });

  $("btn-guardar").addEventListener("click", async () => {
    const r = await fetch("/admin/configuracion/guardar", { method: "POST", body: formData() });
    const data = await r.json();
    rutaNorm.textContent = data.ruta_normalizada || "—";
    pintaResultado(data);
  });

  $("btn-probar").addEventListener("click", async () => {
    pintaResultado({ ok: true, mensaje: "Probando… (puede tardar unos segundos)" });
    const r = await fetch("/admin/configuracion/probar", { method: "POST", body: formData() });
    const data = await r.json();
    pintaResultado(data);
  });

  $("btn-diag").addEventListener("click", async () => {
    const r = await fetch("/admin/configuracion/diagnostico");
    const data = await r.json();
    $("diag-pre").textContent = JSON.stringify(data, null, 2);
    $("diag-pre").parentElement.open = true;
  });

  previewLayout();
})();