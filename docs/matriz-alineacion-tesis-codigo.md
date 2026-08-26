# Matriz de alineación entre tesis y código

Fecha de revisión: 24 de agosto de 2026.

Esta matriz acompaña a `capitulo-desarrollo-secciones-alineadas.tex`. El archivo
LaTeX contiene los reemplazos listos para incorporar al capítulo; esta guía deja
trazabilidad de por qué se modificó cada afirmación.

| Tema | Texto anterior | Estado comprobado | Corrección aplicada |
| --- | --- | --- | --- |
| Base de datos | PostgreSQL implementado como base operativa | La demo y las pruebas funcionan con SQLite; PostgreSQL está soportado por configuración y drivers | SQLite se declara como base validada y PostgreSQL como destino pendiente de validación integral |
| Scraping HTTP | Requests, Beautiful Soup y httpx | Los adaptadores reales usan `aiohttp` | Se reemplazó la lista por `aiohttp` y Playwright |
| Fuentes | Scraping descrito de forma genérica | Existen Carrefour, Jumbo, La Coope y La Anónima | Se documentó la estrategia real de cada adaptador |
| API | Rutas `/api/products`, `/api/prices`, `/api/ranking` | La API usa prefijo `/api/v1` y rutas modulares | Se reemplazó la tabla por los endpoints reales |
| Concurrencia | Workers genéricos con navegadores independientes | `TaskGroup`, `Semaphore`, `Queue`, timeout y un Chromium con contextos/páginas reutilizables | Se describió el modelo exacto y sus límites |
| Paralelismo | El título podía sugerir procesamiento CPU paralelo | No existe `ProcessPoolExecutor` ni cálculo CPU en procesos | Se aclaró que el sistema adopta concurrencia I/O y deja el paralelismo CPU como optimización futura |
| Benchmark | Reducción significativa sin valores | CSV final: 5489 ms secuencial, 4399 ms concurrente, 19,9 % de reducción media | Se incorporaron valores, muestra y límites de generalización |
| ETL | Normalización completa de categorías | El mapeador de categorías sigue pendiente | Se limitó la afirmación a nombres, precios, marcas, unidades, presentación e identidad |
| Identidad | Correspondencia de productos mencionada de forma general | GTIN validado, identidad estructural, consolidación y revisión asistida | Se documentaron reglas conservadoras y auditoría |
| Calidad de precios | No estaba descrita | Vigencia, anomalías históricas y motivos de exclusión están implementados | Se agregó la política de calidad previa al ranking |
| Ubicación | Incorporación de ubicación del usuario | La UI permite usar `navigator.geolocation` y conserva el centro de la ciudad como alternativa | Se documentó el origen seleccionable y el permiso explícito del navegador |
| Mapas | Figuraban como implementados | Leaflet representa origen, ranking y sucursales incompletas sobre OpenStreetMap | Se documentó el componente real y su alcance |
| Coordenadas | No existía trazabilidad de verificación | La migración `0008` registra estado, fuente y fecha; el ranking excluye puntos no verificados | Se agregó la regla de elegibilidad geográfica y su auditoría |
| Actualización | Se afirmaba actualización automática | Scheduler persistente configurable, leases, historial y reintentos sobre el flujo ETL real | La afirmación queda respaldada por la migración `0009`, API y worker FastAPI |
| Alcance | Sistema presentado como solución terminada | Demo integrada para una ciudad y fuentes piloto | Se agregó una subsección explícita de alcance y limitaciones |

## Evidencia del repositorio

- Backend modular en `backend/app/modules/`.
- Rutas reales en `backend/app/api_v1.py` y `interfaces/http/routes.py`.
- Scrapers en `backend/app/modules/ingestion/infrastructure/scrapers/`.
- Concurrencia en `concurrent_refresh_scraping_sources.py`.
- ETL en `load_scraping_run.py` y `infrastructure/etl/`.
- Migraciones `0001` a `0009` en `backend/migrations/versions/`.
- Benchmark real en
  `backend/reports/tesis_benchmark_carrefour_coope_laanonima_20260815_final.csv`.
- Política de calidad en `price_quality_policy.py`.
- Ranking DSS en `decision/application/use_cases/generate_ranking.py`.
- Frontend integrado en `frontend/src/views/CompareView.vue`.
- Mapa de ranking en `frontend/src/components/RankingMap.vue`.

## Estado verificado

- 75 pruebas del backend aprobadas.
- 2 pruebas del frontend aprobadas.
- Build de producción del frontend aprobado.
- SQLite en migración `0009` (`head`).
- Cuatro fuentes activas de scraping en la base de demostración.
- 21 sucursales de demostración, distribuidas en siete cadenas y dos ciudades,
  con coordenadas verificadas y auditables.

## Cambios bibliográficos necesarios

La bibliografía de la tesis debe incorporar una referencia para `aiohttp` si no
existe todavía. Las referencias a Requests, Beautiful Soup y httpx pueden
conservarse en el marco teórico si se analizan como alternativas, pero no deben
figurar como tecnologías utilizadas en esta implementación.
