# Backend DSS Comparador de Precios

## Objetivo

Este backend pertenece a un sistema de apoyo a decisiones (DSS) para comparar precios de supermercados en función de la ubicación del usuario. El sistema permitirá buscar productos, armar una canasta temporal, calcular precios por supermercado, calcular la distancia a las sucursales y generar un ranking multicriterio.

## Arquitectura usada

El proyecto usa un monolito modular con principios de Clean Architecture y Arquitectura Hexagonal. Cada módulo agrupa una responsabilidad funcional y mantiene sus límites de dominio, aplicación, infraestructura e interfaces.

## Capas principales

- `domain`: contiene entidades, objetos de valor, puertos y servicios de dominio. No debe depender de frameworks ni infraestructura.
- `application`: contiene casos de uso, comandos y DTOs. Coordina las reglas de negocio.
- `infrastructure`: contiene adaptadores concretos como PostgreSQL, SQLAlchemy, scrapers, ETL y scheduler.
- `interfaces`: contiene entradas externas como HTTP y CLI.

## Módulos principales

| Módulo | Responsabilidad |
| --- | --- |
| `catalog` | Productos, categorías, marcas y productos por fuente. |
| `supermarkets` | Supermercados, sucursales, ciudades y provincias. |
| `prices` | Precios actuales, históricos y comparación. |
| `basket` | Canasta temporal del usuario anónimo. |
| `geo` | Coordenadas y cálculo de distancia. |
| `decision` | Modelo multicriterio DSS. |
| `ingestion` | Scraping y ETL. |

## Módulos excluidos por ahora

Por ahora no se incluye:

- `users`
- `auth`
- `roles`
- `permissions`
- `sessions`
- `saved_baskets`
- `user_preferences`

## Regla de dependencias

El dominio no debe depender de FastAPI, SQLAlchemy, PostgreSQL, Playwright ni ninguna herramienta externa. Las dependencias deben apuntar hacia el dominio, no al revés.

## Estado inicial y salud

La aplicación expone solamente el endpoint técnico `GET /health`, cuya respuesta es:

```json
{
  "status": "ok",
  "service": "price-dss-backend"
}
```

No existen todavía endpoints de negocio, autenticación, usuarios, modelos SQLAlchemy completos ni persistencia de canastas.

## Desarrollo local

Desde la carpeta `backend`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

La documentación automática de FastAPI estará disponible en `http://127.0.0.1:8000/docs` y el estado del servicio en `http://127.0.0.1:8000/health`.

## Próximos pasos

- Definir entidades de dominio.
- Crear puertos de repositorio.
- Implementar modelos SQLAlchemy.
- Implementar casos de uso.
- Crear endpoints HTTP.
- Implementar scraping.
- Implementar pipeline ETL.
- Implementar ranking multicriterio.

## Migraciones de base de datos

Configura `DATABASE_URL` con una URL PostgreSQL asíncrona. Por ejemplo, en PowerShell:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://dss_user:change_me@localhost:5432/price_dss"
```

Alembic adapta automáticamente el driver `asyncpg` a `psycopg` para ejecutar migraciones. Desde `backend`, usa:

```bash
alembic revision --autogenerate -m "create initial price dss schema"
alembic upgrade head
alembic downgrade -1
```

## Seed inicial

Aplica primero las migraciones y luego carga los datos de prueba para Comodoro Rivadavia y Rada Tilly:

```bash
alembic upgrade head
python scripts/seed_initial_data.py
```

También puede ejecutarse con `python -m scripts.seed_initial_data`. El seed es idempotente y usa una fecha de relevamiento fija para no duplicar precios históricos.

## Unit of Work

La unidad de trabajo agrupa repositorios que comparten una sesión y centraliza el `commit` o `rollback`. Los repositorios solo hacen `flush`; los futuros casos de uso decidirán cuándo confirmar la transacción.

```python
async with get_unit_of_work() as uow:
    products = await uow.products.search_by_name("coca")
    await uow.commit()
```

Para una prueba de solo lectura de la conexión, ejecuta `python scripts/test_uow_connection.py` después de aplicar las migraciones.
