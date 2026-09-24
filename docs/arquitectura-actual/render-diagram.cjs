// Generates the editable SVG and a print-resolution PNG from the same layout.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');

const W = 1600;
const H = 1260;
const parts = [];
const ink = '#202b31';
const muted = '#526269';
const green = '#197158';
const rust = '#a04346';
const blue = '#28617c';
const xml = (value) => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');

function rect(x, y, w, h, fill = '#ffffff', stroke = '#c4ced0', radius = 8) {
  parts.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="1.6"/>`);
}
function text(x, y, value, size = 20, color = ink, weight = 400, anchor = 'start') {
  parts.push(`<text x="${x}" y="${y}" font-size="${size}" fill="${color}" font-weight="${weight}" text-anchor="${anchor}">${xml(value)}</text>`);
}
function lines(x, y, values, size = 19, color = muted, step = 29) {
  values.forEach((value, index) => text(x, y + index * step, value, size, color));
}
function arrow(d, color = ink, both = false, dashed = false) {
  const marker = color === green ? 'green' : color === rust ? 'rust' : color === blue ? 'blue' : 'ink';
  parts.push(`<path d="${d}" fill="none" stroke="${color}" stroke-width="2.2" marker-end="url(#${marker})"${both ? ` marker-start="url(#${marker})"` : ''}${dashed ? ' stroke-dasharray="7 5"' : ''}/>`);
}

text(40, 52, 'Arquitectura actual del sistema DSS', 34, ink, 700);
text(40, 86, 'Comparador de precios por ubicaci\u00f3n | Vista l\u00f3gica de componentes', 20, muted);
text(1560, 52, '14 SEP 2026', 16, muted, 600, 'end');

rect(40, 125, 240, 128, '#f5f7f7');
text(62, 163, 'Usuario', 25, ink, 700);
lines(62, 196, ['Canasta y cantidades', 'Ubicaci\u00f3n y preferencias'], 18);

rect(360, 125, 675, 128, '#eef6f3', green);
text(385, 160, 'Frontend web | Vue 3 + TypeScript', 25, green, 700);
lines(385, 191, ['Router + Pinia | Canasta en localStorage', 'Cat\u00e1logo, modal, precios, ranking y mapa Leaflet'], 19);
arrow('M 285 190 H 352', ink, true);

rect(1140, 125, 420, 128, '#f7f8f8');
text(1163, 160, 'Recursos del navegador', 23, ink, 700);
lines(1163, 191, ['Geolocalizaci\u00f3n del dispositivo', 'Mapas OSM e im\u00e1genes por URL'], 18);
arrow('M 1040 190 H 1132', ink, true, true);
text(945, 289, 'HTTP / JSON', 17, muted);

rect(40, 325, 1520, 555, '#f7f9f8', '#9badb1', 8);
text(64, 356, 'BACKEND: MONOLITO MODULAR | FastAPI + Python', 21, ink, 700);
rect(80, 380, 1440, 65, '#ffffff', '#9badb1');
arrow('M 925 258 V 378', ink, true);
text(105, 419, 'Adaptadores HTTP /api/v1  |  Validaci\u00f3n de entradas, DTO y manejo de errores', 22, ink, 600);
arrow('M 300 445 V 480', green);
arrow('M 780 445 V 480', blue);
arrow('M 1280 445 V 480', rust);

rect(80, 490, 440, 210, '#eef6f3', green);
text(103, 526, 'Ingesta y calidad de datos', 24, green, 700);
lines(103, 558, [
  'Actualizaci\u00f3n manual + scheduler opcional',
  'asyncio: tareas, sem\u00e1foros y cola',
  'Staging, validaci\u00f3n y carga ETL',
  'Regex + GTIN + reglas + RapidFuzz',
  'Ambig\u00fcedad y revisi\u00f3n de identidad',
], 18, ink, 28);

rect(560, 490, 440, 210, '#f0f6f9', blue);
text(583, 526, 'Cat\u00e1logo y b\u00fasqueda', 24, blue, 700);
lines(583, 558, [
  '1. Coincidencias textuales primero',
  '2. Si no hay, candidatos sem\u00e1nticos',
  '3. Verificar activos en PostgreSQL',
  'Sin fusi\u00f3n de identidades por vectores',
  'Detalle de precios, marcas e im\u00e1genes',
], 18, ink, 28);

rect(1040, 490, 480, 210, '#fcf1f1', rust);
text(1063, 526, 'Comparaci\u00f3n y decisi\u00f3n', 24, rust, 700);
lines(1063, 558, [
  'Canasta y sucursales elegibles',
  'Vigencia, disponibilidad y anomal\u00edas',
  'Precio propio o referencia de la cadena',
  'Distancias Haversine + pesos del usuario',
  'Ranking mediante suma ponderada (WSM)',
], 18, ink, 28);

arrow('M 300 704 V 756', green);
arrow('M 780 704 V 756', blue);
arrow('M 1280 704 V 756', rust);
rect(80, 767, 1440, 82, '#ffffff', '#9badb1');
text(103, 797, 'Puertos y adaptadores de infraestructura', 21, ink, 700);
text(103, 828, 'ScraperPort: aiohttp / Playwright', 18, muted);
text(583, 828, 'UnitOfWorkPort: SQLAlchemy / Alembic', 18, muted);
text(1090, 828, 'ProductSearchIndexPort: Chroma / E5', 18, muted);

arrow('M 300 851 V 942', green, true);
arrow('M 780 851 V 942', ink, true);
arrow('M 1280 851 V 942', blue, true);
text(318, 915, 'HTTP / navegador', 17, green);
text(800, 915, 'Transacciones SQL', 17, muted);
text(1300, 915, 'API local embebida', 17, blue);

rect(80, 955, 440, 178, '#eef6f3', green);
text(103, 991, 'Fuentes externas', 24, green, 700);
lines(103, 1024, [
  'Carrefour, Chango M\u00e1s y Jumbo',
  'La Coope, La An\u00f3nima y Maxiconsumo',
  'Cat\u00e1logos p\u00fablicos: HTTP / JSON / HTML',
], 18, ink, 29);
text(103, 1111, 'Extracci\u00f3n; no confirma stock f\u00edsico.', 17, muted);

rect(560, 955, 440, 178, '#f5f7f7', '#6a7c83');
text(583, 991, 'PostgreSQL', 25, ink, 700);
lines(583, 1024, [
  'Datos de negocio y trazabilidad',
  'Productos, publicaciones, precios y sedes',
  'Staging, revisiones y planes de ingesta',
], 18, ink, 29);
text(583, 1111, 'Persistencia principal; fuente de verdad.', 17, muted);

rect(1040, 955, 480, 178, '#f0f6f9', blue);
text(1063, 991, 'ChromaDB persistente local', 25, blue, 700);
lines(1063, 1024, [
  'Embeddings: multilingual-e5-small',
  'Colecci\u00f3n product_search_v1 | coseno',
  'Archivos: backend/.chroma/product_search',
], 18, ink, 29);
text(1063, 1111, '\u00cdndice derivado; no es una tabla PostgreSQL.', 17, muted);

parts.push('<path d="M 40 1170 H 1560" stroke="#c4ced0"/>');
text(40, 1201, 'Identidad: reglas conservadoras. B\u00fasqueda: similitud. Decisi\u00f3n: WSM. Son responsabilidades distintas.', 20, ink, 600);
text(40, 1231, 'El ETL confirma primero en PostgreSQL y luego intenta indexar productos nuevos. El \u00edndice se puede reconstruir por script.', 18, muted);

const markers = [['ink', ink], ['green', green], ['rust', rust], ['blue', blue]].map(([id, color]) =>
  `<marker id="${id}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto-start-reverse"><path d="M 0 0 L 8 4 L 0 8 Z" fill="${color}"/></marker>`
).join('');
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="title description"><title id="title">Arquitectura actual del sistema DSS</title><desc id="description">Cliente Vue y backend FastAPI modular con ingesta, catalogo, busqueda y ranking. Puertos hacia seis fuentes, PostgreSQL y Chroma local.</desc><defs>${markers}</defs><rect width="100%" height="100%" fill="white"/><g font-family="Segoe UI, Arial, sans-serif">${parts.join('\n')}</g></svg>`;

async function main() {
  fs.writeFileSync(path.join(__dirname, 'arquitectura-actual.svg'), svg, 'utf8');
  await sharp(Buffer.from(svg)).resize(W * 2, H * 2).png().toFile(path.join(__dirname, 'arquitectura-actual.png'));
  console.log('Generated arquitectura-actual.svg and arquitectura-actual.png');
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
