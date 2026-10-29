# Despliegue en Render

Esta configuración publica el sitio, la API y la base PostgreSQL. La actualización
de precios se realiza bajo demanda desde la interfaz: al presionar **Actualizar
precios**, la API ejecuta los scrapers seleccionados y luego el ETL.

## Servicios creados por `render.yaml`

| Recurso | Función |
| --- | --- |
| `price-dss-frontend` | Compila y publica Vue como sitio estático. |
| `price-dss-api` | Expone FastAPI y aplica migraciones al iniciar. |
| `price-dss-postgres` | Base relacional, historial de precios y vectores `pgvector`. |

No se crea un Cron Job ni un worker permanente, por lo que la configuración puede
usarse sin ese costo. El código de scheduler permanece en el proyecto para una
etapa posterior, pero queda desactivado en producción.

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
7. Abrir el frontend, seleccionar una o dos fuentes y usar **Actualizar precios**
   para validar el scraping bajo demanda. Revisar los logs de la API y las tablas
   de auditoría después de la ejecución.

## Variables relevantes

La API recibe `DATABASE_URL` desde Render. El scheduler embebido y las
actualizaciones automáticas permanecen desactivados.

```env
INGESTION_SCHEDULER_ENABLED=false
INGESTION_SCHEDULER_EMBEDDED_ENABLED=false
VECTOR_SEARCH_ENABLED=true
VECTOR_EMBEDDING_MODEL=intfloat/multilingual-e5-small
VECTOR_EMBEDDING_DIMENSIONS=384
```

El modelo de embeddings se descarga al iniciar el primer proceso que necesita
búsqueda semántica. Elegir un plan con memoria suficiente para la API,ნესpecialmente cuando el usuario ejecute fuentes que usan Playwright.

## Operación segura

- Empezar con una fuente y permitir al usuario actualizar manualmente; incrementar
  cobertura luego de verificar tiempos, memoria y respuestas de cada supermercado.
- Limitar la concurrencia de fuentes para no bloquear la respuesta HTTP ni agotar
  la memoria de la instancia gratuita.
- Las tareas largas deben cerrar Playwright correctamente y respetar límites de
  concurrencia, reintentos y los términos de uso de cada sitio.
- Reindexar vectores tras una carga inicial con:

```bash
python scripts/reindex_product_search_vectors.py --reset
```
