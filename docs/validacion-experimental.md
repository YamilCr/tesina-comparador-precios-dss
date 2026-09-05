# Validacion experimental

La validacion se ejecuta con datos y algoritmos del proyecto y genera artefactos
auditables mediante:

```powershell
cd backend
uv run python scripts/run_experimental_validation.py `
  --benchmark-csv reports/tesis_benchmark_4_cadenas_20260826.csv `
  --output-dir reports/experimental_validation_20260826
```

## Rendimiento concurrente

El benchmark real incluyo Carrefour, Jumbo, La Anonima y La Coope. Se utilizaron
las consultas `coca cola` y `leche`, limite de cinco resultados, una vuelta de
calentamiento y cinco repeticiones emparejadas por modo. El orden
secuencial/concurrente se alterno para reducir el sesgo temporal.

| Modo | Media | Mediana | Desvio | P95 | Throughput | Exito |
|---|---:|---:|---:|---:|---:|---:|
| Secuencial | 6427,6 ms | 6441 ms | 368,2 ms | 6837 ms | 6,08 items/s | 100% |
| Concurrente | 3855,6 ms | 4050 ms | 391,8 ms | 4239 ms | 10,20 items/s | 100% |

La concurrencia obtuvo un speedup de `1,67x` y una reduccion media de duracion
del `40,0%`, procesando los mismos 39 items por ejecucion. La Anonima fue el
camino critico: su adaptador Playwright promedio 3618 ms en modo concurrente,
frente a 1268 ms para Carrefour, 568 ms para Jumbo y 455 ms para La Coope.

## Cobertura por cadena

La cobertura se calcula desde SQLite y distingue sucursales, fuentes reales,
publicaciones canonicas, precios disponibles y resultados ETL. El indicador de
cobertura sucursal-producto usa observaciones disponibles del historial; no
afirma stock actual simultaneo en todas las sucursales.

| Cadena | Sucursales | Fuentes | Productos publicados | Con precio | Exito de corridas |
|---|---:|---:|---:|---:|---:|
| Carrefour | 2 | 1 | 72 | 72 | 100,0% |
| Chango Mas | 2 | 1 | 9 | 9 | 100,0% |
| Diarco | 1 | 0 | 5 | 0 | Sin corridas |
| Jumbo | 1 | 1 | 104 | 100 | 98,4% |
| La Anonima | 8 | 1 | 74 | 74 | 85,5% |
| La Coope | 6 | 1 | 99 | 95 | 98,9% |
| Maxiconsumo | 1 | 1 | 23 | 18 | 100,0% |

Esta medicion muestra que sumar sucursales no equivale a tener cobertura de
precios. Chango Mas y Maxiconsumo ya incorporan fuentes reales con historial;
Diarco conserva geografia configurada, pero aun no tiene adaptador ni precios.

## Calidad del matching

El conjunto versionado contiene diez productos canonicos y 36 casos etiquetados:
22 positivos y 14 negativos. Incluye equivalencias de unidades, descriptores,
variantes, marcas incompatibles y tamanos distintos.

| Metrica | Resultado |
|---|---:|
| Precision | 1,0000 |
| Recall | 0,8636 |
| F1 | 0,9268 |
| Accuracy | 0,9167 |
| Falsos positivos | 0 |
| Falsos negativos | 3 |

Los tres falsos negativos corresponden a `sin azucar`, `parcialmente descremada`
y el orden alternativo `Gancia Americano`. El comportamiento confirma la regla
conservadora: ante evidencia semantica insuficiente el sistema se abstiene y no
fusiona identidades incorrectas.

## Sensibilidad de pesos

Se recorrio el simplex completo con paso `0,05`, generando 231 combinaciones que
suman uno. El escenario controlado usa cuatro alternativas basadas en los precios
del seed y distancias del piloto. La referencia coincide con el sistema:
precio `0,6`, distancia `0,3` y ahorro `0,1`.

| Ganador | Escenarios | Participacion |
|---|---:|---:|
| Chango Mas - Hiper Enrique Girolamo | 140 | 60,6% |
| Carrefour - Pellegrini | 63 | 27,3% |
| La Anonima - Alem | 28 | 12,1% |

El ganador base conserva el primer puesto en el `60,6%` de las combinaciones.
La correlacion de Spearman media contra el orden base es `0,8017`. El resultado
es razonablemente robusto, aunque una preferencia mayor por cercania cambia la
recomendacion hacia Carrefour o La Anonima.

## Amenazas de validez

- Los tiempos dependen de red, disponibilidad y cambios de los sitios externos.
- Cinco repeticiones permiten estadistica descriptiva, no inferencia poblacional.
- El matching se evalua sobre un conjunto curado; debe ampliarse con revision
  humana de mas categorias y cadenas.
- La sensibilidad utiliza un escenario controlado para aislar los pesos; no
  representa todas las canastas posibles.
- Las mediciones locales usan SQLite. PostgreSQL requiere una repeticion
  equivalente antes del despliegue productivo.

Los CSV individuales, el resumen JSON y el informe generado se encuentran en
`backend/reports/experimental_validation_20260826/`.
