# Despliegue en Render

Esta configuración separa el sitio público, la API y la actualización programada
de precios. Los dos procesos de backend usan la misma base PostgreSQL y el índice
semántico queda en `pgvector`, por lo que no depende de archivos locales.

## Servicios creados por `render.yaml`

| Recurso | Función |
| --- | --- |
| `price-dss-frontend` | Compila y publica Vue como sitio estático. |
| `price-dss-api` | Expone FastAPI y aplica migraciones al iniciar. |
| `price-dss-ingestion` | Cron que cada diez minutos busca los planes vencidos y ejecuta scraping + ETL. |
| `price-dss-postgres` | Base relacional, historial de precios y vectores `pgvector`. |

La frecuencia efectiva de cada supermercado no es diez minutos: la determina
`interval_minutes` de su plan en `scraping_schedule`. El cron solo despierta el
proceso para reclamar los planes que ya vencieron.

## Preparación antes del primer despliegue

1. Subir la rama `servidor` a un repositorio de GitHub.
2. En Render, seleccionar **New > Blueprint** y elegir ese repositorio.
3. Confirmar la creación de los cuatro recursos del archivo `render.yaml`.
4. Cuando Render pida los valores manuales, completar:
   - `CORS_ORIGINS` de `price-dss-api` con la URL final del frontend, entre
     corchetes JSON. Ejemplo: `["https://price-dss-frontend.onrender.com"]`.
   - `VITE_API_BASE_URL` de `price-dss-frontend` con la URL final de la API.
     Ejemplo: `https://price-dss-api.onrender.com`.
5. Desplegar primero la API. Al iniciar, ejecuta `alembic upgrade head`, que
   habilita la extensión PostgreSQL `vector` y crea `product_search_vector`.
6. Ejecutar una vez el seed o migrar los datos iniciales al PostgreSQL remoto.
   No cargar datos reales desde SQLite sin antes hacer una copia de seguridad.
7. En Render, abrir el cron `price-dss-ingestion` y usar **Trigger Run** para
   validar una ejecución. Luego revisar sus logs y las tablas de auditoría.

## Variables relevantes

En producción, tanto API como cron requieren el mismo `DATABASE_URL`, provisto
por Render. La API deja desactivado el scheduler embebido; el cron es el único
proceso que ejecuta actualizaciones automáticas.

```env
INGESTION_SCHEDULER_ENABLED=true
INGESTION_SCHEDULER_EMBEDDED_ENABLED=false
VECTOR_SEARCH_ENABLED=true
VECTOR_EMBEDDING_MODEL=intfloat/multilingual-e5-small
VECTOR_EMBEDDING_DIMENSIONS=384
```

El modelo de embeddings se descarga al iniciar el primer proceso que necesita
búsqueda semántica. Elegir un plan con memoria suficiente para API y cron,
especialmente en las fuentes que usan Playwright.

## Operación segura

- Empezar con una fuente y un plan diario; incrementar cobertura luego de
  verificar tiempos, memoria y respuestas de cada supermercado.
- No ejecutar dos cron jobs que procesen los mismos planes. El plan tiene un
  lease en la base, pero un único cron simplifica la operación.
- Las tareas largas deben cerrar Playwright correctamente y respetar límites de
  concurrencia, reintentos y los términos de uso de cada sitio.
- Reindexar vectores tras una carga inicial con:

```bash
python scripts/reindex_product_search_vectors.py --reset
```
