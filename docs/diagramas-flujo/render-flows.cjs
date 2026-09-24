// Editable flowchart definitions. Generates SVG and print-resolution PNG files.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');

const colors = { ink: '#233238', muted: '#53676e', green: '#197158', blue: '#28617c', red: '#a04346' };
const esc = (s) => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');

class Flow {
  constructor(name, w, h, title, subtitle) {
    Object.assign(this, { name, w, h, title, subtitle });
    this.nodes = [];
    this.edges = [];
    this.labels = [];
  }
  text(x, y, value, size = 19, color = colors.ink, weight = 400, anchor = 'middle') {
    return `<text x="${x}" y="${y}" text-anchor="${anchor}" font-size="${size}" fill="${color}" font-weight="${weight}">${esc(value)}</text>`;
  }
  block(x, y, lines, { w = 470, h = 86, kind = 'process', color = 'blue', size = 21 } = {}) {
    const c = colors[color];
    let shape;
    if (kind === 'decision') {
      shape = `<path d="M ${x} ${y-h/2} L ${x+w/2} ${y} L ${x} ${y+h/2} L ${x-w/2} ${y} Z" fill="#fff8df" stroke="#8f7940" stroke-width="2"/>`;
    } else {
      const fill = kind === 'terminal' ? '#eef6f3' : color === 'red' ? '#fcf1f1' : '#f2f7f9';
      shape = `<rect x="${x-w/2}" y="${y-h/2}" width="${w}" height="${h}" rx="${kind === 'terminal' ? h/2 : 6}" fill="${fill}" stroke="${c}" stroke-width="1.8"/>`;
    }
    const step = size + 7;
    const top = y - ((lines.length - 1) * step) / 2 + size * 0.34;
    this.nodes.push(shape + lines.map((s, i) => this.text(x, top+i*step, s, size, colors.ink, i === 0 ? 600 : 400)).join(''));
  }
  decision(x, y, lines) { this.block(x, y, lines, { kind: 'decision', w: 420, h: 132, size: 20 }); }
  terminal(x, y, label, w = 300) { this.block(x, y, [label], { kind: 'terminal', w, h: 58, color: 'green', size: 21 }); }
  edge(d, label, x, y, color = 'ink', dashed = false) {
    this.edges.push(`<path d="${d}" fill="none" stroke="${colors[color]}" stroke-width="2" marker-end="url(#arrow-${color})"${dashed ? ' stroke-dasharray="6 5"' : ''}/>`);
    if (label) this.labels.push(this.text(x, y, label, 18, colors[color], 600));
  }
  note(y, lines) {
    this.labels.push(`<path d="M 40 ${y-28} H ${this.w-40}" stroke="#cad3d6"/>`);
    lines.forEach((line, i) => this.labels.push(this.text(40, y+i*27, line, 18, colors.muted, 400, 'start')));
  }
  svg() {
    const markers = Object.entries(colors).map(([key, c]) => `<marker id="arrow-${key}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M 0 0 L 8 4 L 0 8 Z" fill="${c}"/></marker>`).join('');
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${this.w}" height="${this.h}" viewBox="0 0 ${this.w} ${this.h}" role="img" aria-labelledby="title"><title id="title">${esc(this.title)}</title><defs>${markers}</defs><rect width="100%" height="100%" fill="white"/><g font-family="Segoe UI, Arial, sans-serif">${this.text(40, 49, this.title, 32, colors.ink, 700, 'start')}${this.text(40, 83, this.subtitle, 19, colors.muted, 400, 'start')}${this.edges.join('')}${this.nodes.join('')}${this.labels.join('')}</g></svg>`;
  }
  async save() {
    const svg = this.svg();
    fs.writeFileSync(path.join(__dirname, `${this.name}.svg`), svg, 'utf8');
    await sharp(Buffer.from(svg)).resize(this.w*2, this.h*2).png().toFile(path.join(__dirname, `${this.name}.png`));
    console.log(`${this.name}: ${this.w*2} x ${this.h*2}`);
  }
}

function general() {
  const f = new Flow('flujo-general', 1500, 1820, 'Flujo general del sistema DSS', 'Interacci\u00f3n del usuario | Cat\u00e1logo, actualizaci\u00f3n y ranking | 14 SEP 2026');
  f.terminal(750, 140, 'Inicio');
  f.block(750, 250, ['Abrir comparador']);
  f.decision(750, 380, ['\u00bfActualizar', 'precios?']);
  f.block(240, 380, ['Ejecutar actualizaci\u00f3n ETL', 'Consultar estado por fuente'], { w: 360, h: 100, color: 'green', size: 19 });
  f.block(750, 530, ['Consultar cat\u00e1logo o buscar', 'Flujo textual / sem\u00e1ntico']);
  f.decision(750, 660, ['\u00bfHay productos', 'para mostrar?']);
  f.block(1250, 660, ['Sin coincidencias'], { w: 330, color: 'red' });
  f.block(1250, 530, ['Reformular consulta'], { w: 330, size: 20 });
  f.block(750, 815, ['Consultar detalle y precios', 'Agregar productos y cantidades'], { h: 98 });
  f.block(750, 940, ['Definir ubicaci\u00f3n y pesos', 'Solicitar comparaci\u00f3n'], { h: 98 });
  f.decision(750, 1070, ['\u00bfLa solicitud', 'es v\u00e1lida?']);
  f.block(240, 1070, ['Informar error de entrada'], { w: 360, color: 'red', size: 20 });
  f.block(240, 940, ['Corregir datos de la solicitud'], { w: 360, size: 19 });
  f.block(750, 1220, ['Obtener sucursales elegibles', 'Precios v\u00e1lidos y costo de canasta', 'Precio propio o referencia de cadena'], { h: 110, size: 20 });
  f.decision(750, 1360, ['\u00bfHay alternativas', 'con canasta completa?']);
  f.block(1250, 1360, ['Mostrar faltantes o', 'ausencia de alternativas', 'No generar recomendaci\u00f3n'], { w: 330, h: 118, color: 'red', size: 19 });
  f.block(750, 1500, ['Calcular distancia y ahorro', 'Normalizar, aplicar WSM y ordenar'], { h: 98, size: 20 });
  f.block(750, 1625, ['Mostrar ranking, costos y mapa']);
  f.terminal(750, 1730, 'Fin de la comparaci\u00f3n', 380);
  f.edge('M 750 169 V 207');
  f.edge('M 750 293 V 314');
  f.edge('M 540 380 H 420', 'S\u00ed', 480, 365, 'green');
  f.edge('M 750 446 V 487', 'No', 780, 471);
  f.edge('M 240 430 V 468 H 750 V 487', null, 0, 0, 'green');
  f.edge('M 750 573 V 594');
  f.edge('M 960 660 H 1085', 'No', 1020, 645, 'red');
  f.edge('M 1250 617 V 573', null, 0, 0, 'red');
  f.edge('M 1085 530 H 985');
  f.edge('M 750 726 V 766', 'S\u00ed', 780, 752, 'green');
  f.edge('M 750 864 V 891');
  f.edge('M 750 989 V 1004');
  f.edge('M 540 1070 H 420', 'No', 480, 1055, 'red');
  f.edge('M 240 1027 V 983', null, 0, 0, 'red');
  f.edge('M 420 940 H 515');
  f.edge('M 750 1136 V 1165', 'S\u00ed', 780, 1157, 'green');
  f.edge('M 750 1275 V 1294');
  f.edge('M 960 1360 H 1085', 'No', 1020, 1345, 'red');
  f.edge('M 1250 1419 V 1730 H 940', null, 0, 0, 'red');
  f.edge('M 750 1426 V 1451', 'S\u00ed', 780, 1446, 'green');
  f.edge('M 750 1549 V 1582');
  f.edge('M 750 1668 V 1701');
  f.note(1790, ['La actualizaci\u00f3n es opcional: buscar no ejecuta scraping. La ausencia de alternativas no conduce a una recomendaci\u00f3n.']);
  return f;
}

function search() {
  const f = new Flow('flujo-busqueda-semantica', 1500, 1530, 'Flujo de b\u00fasqueda de productos', 'Consulta no vac\u00eda | Texto primero, Chroma como recuperaci\u00f3n alternativa | 14 SEP 2026');
  f.terminal(750, 145, 'Recibir consulta', 320);
  f.block(750, 270, ['Buscar coincidencias textuales', 'Aplicar filtro de categor\u00eda']);
  f.decision(750, 410, ['\u00bfHay coincidencias', 'textuales?']);
  f.block(240, 410, ['Conservar resultados textuales', 'No consultar Chroma'], { w: 360, h: 98, color: 'green', size: 19 });
  f.block(750, 565, ['Consultar Chroma si est\u00e1 habilitado', 'E5: query: + similitud coseno', 'top_k = min(l\u00edmite * 3, 50)'], { h: 110, size: 20 });
  f.decision(750, 710, ['\u00bfSe pudo consultar', 'el \u00edndice?']);
  f.block(1250, 710, ['Si hay fallo: registrar aviso', 'Si est\u00e1 deshabilitado: omitir'], { w: 360, h: 98, color: 'red', size: 19 });
  f.block(750, 855, ['Aplicar umbral de similitud', 'Conservar IDs candidatos']);
  f.block(750, 980, ['Verificar activos en PostgreSQL', 'Aplicar filtro de categor\u00eda']);
  f.decision(750, 1120, ['\u00bfQuedan productos', 'v\u00e1lidos?']);
  f.block(1250, 1120, ['Conservar resultado textual vac\u00edo', 'Sin coincidencias para devolver'], { w: 380, h: 98, color: 'red', size: 18 });
  f.block(750, 1285, ['Devolver productos o lista vac\u00eda', 'Sin duplicados ni score sem\u00e1ntico'], { h: 98, size: 20 });
  f.terminal(750, 1400, 'Fin de la consulta', 350);
  f.edge('M 750 174 V 227');
  f.edge('M 750 313 V 344');
  f.edge('M 540 410 H 420', 'S\u00ed', 480, 393, 'green');
  f.edge('M 240 459 V 1285 H 515', null, 0, 0, 'green');
  f.edge('M 750 476 V 510', 'No', 780, 500);
  f.edge('M 750 620 V 644');
  f.edge('M 960 710 H 1070', 'No', 1015, 692, 'red');
  f.edge('M 1250 759 V 1071', null, 0, 0, 'red');
  f.edge('M 750 776 V 812', 'S\u00ed', 780, 798, 'green');
  f.edge('M 750 898 V 937');
  f.edge('M 750 1023 V 1054');
  f.edge('M 960 1120 H 1060', 'No', 1010, 1103, 'red');
  f.edge('M 1250 1169 V 1285 H 985', null, 0, 0, 'red');
  f.edge('M 750 1186 V 1236', 'S\u00ed', 780, 1215, 'green');
  f.edge('M 750 1334 V 1371');
  f.note(1470, ['Si la consulta est\u00e1 vac\u00eda, se lista el cat\u00e1logo activo paginado sin recorrer este flujo.', 'La b\u00fasqueda sem\u00e1ntica recupera candidatos: no aprueba equivalencias ni fusiona productos.']);
  return f;
}

function ingestion() {
  const f = new Flow('flujo-etl-identidad', 1780, 2070, 'Flujo ETL y resoluci\u00f3n de identidad', 'Extracci\u00f3n por fuente y procesamiento por registro | 14 SEP 2026');
  f.terminal(850, 145, 'Inicio manual / plan / script', 470);
  f.block(850, 280, ['Ejecutar scrapers concurrentemente', 'aiohttp / Playwright + l\u00edmites', 'Entregar resultados a la cola'], { h: 110, size: 20 });
  f.decision(850, 420, ['\u00bfLa extracci\u00f3n', 'de la fuente fue exitosa?']);
  f.block(240, 420, ['Registrar fallo de la fuente', 'Las dem\u00e1s fuentes contin\u00faan'], { w: 390, h: 100, color: 'red', size: 19 });
  f.terminal(240, 550, 'Fin de esta fuente', 330);
  f.block(850, 560, ['Guardar corrida y datos en staging', 'Iniciar procesamiento de registros'], { h: 90, size: 20 });
  f.block(850, 690, ['Validar, limpiar y normalizar', 'Precio, regex, unidades y packs'], { h: 90 });
  f.decision(850, 825, ['\u00bfEl registro es v\u00e1lido', 'y no est\u00e1 duplicado?']);
  f.block(240, 825, ['Marcar rechazado o duplicado', 'Conservar el motivo'], { w: 390, h: 98, color: 'red', size: 19 });
  f.block(850, 960, ['Resolver identidad del producto', 'Publicaci\u00f3n / GTIN / restricciones', 'Reglas estructurales + RapidFuzz'], { h: 110, size: 20 });
  f.decision(850, 1100, ['\u00bfLa identidad', 'es ambigua?']);
  f.block(1450, 1100, ['Conservar como unmatched', 'Motivo y candidatos para revisi\u00f3n', 'No crear un duplicado por la duda'], { w: 430, h: 118, color: 'red', size: 19 });
  f.decision(850, 1245, ['\u00bfExiste un producto', 'can\u00f3nico identificado?']);
  f.block(240, 1245, ['Crear producto nuevo', 'Si la carga permite crearlo'], { w: 390, h: 98, color: 'green', size: 19 });
  f.block(850, 1400, ['Guardar publicaci\u00f3n y precio', 'Conservar enlaces de im\u00e1genes', 'Marcar el registro como cargado'], { h: 110, size: 20 });
  f.decision(850, 1565, ['\u00bfQuedan registros', 'por procesar?']);
  f.block(850, 1710, ['Confirmar transacci\u00f3n PostgreSQL', 'Productos, precios y estados ETL'], { h: 98, size: 20 });
  f.block(850, 1840, ['Intentar upsert en Chroma', 'Solo productos nuevos de la carga'], { h: 98, size: 20 });
  f.block(1450, 1840, ['Si falla: warning y futura reindexaci\u00f3n', 'No revertir la carga ya confirmada'], { w: 470, h: 98, color: 'red', size: 19 });
  f.terminal(850, 1960, 'Fin de la carga', 320);
  f.edge('M 850 174 V 225');
  f.edge('M 850 335 V 354');
  f.edge('M 640 420 H 435', 'No', 540, 402, 'red');
  f.edge('M 240 470 V 521', null, 0, 0, 'red');
  f.edge('M 850 486 V 515', 'S\u00ed', 885, 507, 'green');
  f.edge('M 850 605 V 645');
  f.edge('M 850 735 V 759');
  f.edge('M 640 825 H 435', 'No', 540, 807, 'red');
  f.edge('M 240 874 V 990 H 20 V 1480 H 850 V 1499', null, 0, 0, 'red');
  f.edge('M 850 891 V 905', 'S\u00ed', 890, 896, 'green');
  f.edge('M 850 1015 V 1034');
  f.edge('M 1060 1100 H 1235', 'S\u00ed', 1145, 1082, 'red');
  f.edge('M 1450 1159 V 1480 H 850 V 1499', null, 0, 0, 'red');
  f.edge('M 850 1166 V 1179', 'No', 885, 1179);
  f.edge('M 640 1245 H 435', 'No', 540, 1227, 'green');
  f.edge('M 240 1294 V 1400 H 615', null, 0, 0, 'green');
  f.edge('M 850 1311 V 1345', 'S\u00ed', 885, 1335, 'green');
  f.edge('M 850 1455 V 1499');
  f.edge('M 1060 1565 H 1720 V 690 H 1085', 'S\u00ed: siguiente registro', 1410, 1548);
  f.edge('M 850 1631 V 1661', 'No', 885, 1653);
  f.edge('M 850 1759 V 1791');
  f.edge('M 1085 1840 H 1215', 'Fallo', 1150, 1820, 'red', true);
  f.edge('M 850 1889 V 1931');
  f.edge('M 1450 1889 V 1960 H 1010', null, 0, 0, 'red', true);
  f.note(2020, ['Flujo resumido con creaci\u00f3n habilitada (valor predeterminado). Sin ella, los productos nuevos quedan sin asociar.', 'La revisi\u00f3n y consolidaci\u00f3n auditada es un proceso posterior; Chroma no interviene en la decisi\u00f3n de identidad.']);
  return f;
}

async function main() {
  for (const diagram of [general(), search(), ingestion()]) await diagram.save();
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
