# Sustituciones de productos por sucursal

## Alcance

El comparador permite completar una canasta con reemplazos elegidos expresamente por el usuario para una sucursal. La lista persistida en el navegador, las identidades canonicas, el ETL y los scrapers no cambian. No hay tablas, migraciones ni dependencias nuevas.

Las sucursales incompletas se ordenan por cantidad de productos faltantes y luego por distancia. La interfaz muestra las primeras tres y permite consultar las restantes. No se consideran mas economicas ni participan del ranking mientras tengan faltantes.

## Compatibilidad

`decision/domain/services/substitution_policy.py` es independiente de `ProductIdentityMatcher`:

- Permite cambiar de marca explicitamente informada.
- Exige igualdad de cantidad en unidad base, unidad y pack. Por ejemplo, 1 kg equivale a 1000 g; no se convierte la cantidad de compra ni se reemplazan dos envases chicos por uno grande.
- Compara conjuntos de tokens normalizados del nombre y de la descripcion, si existe. Retira la marca explicita, la presentacion y articulos/conectores neutros. Conserva calificadores como integral, entera, original, sin, gluten, lactosa o azucar.
- Admite plurales regulares, abreviaturas `c/` y `s/`, y como maximo una letra interna omitida/agregada en una palabra larga (al menos ocho letras, mismos tres caracteres iniciales y finales). Usa la distancia Levenshtein de RapidFuzz, ya instalado. Cada palabra debe tener una correspondencia unica; no basta una similitud global alta.
- Puede reconocer ese mismo error de una letra en una marca de una sola palabra, solo si la marca ya esta informada en el producto y no aparece escrita exactamente. No infiere marcas ausentes.
- No omite palabras sobrantes, negaciones ni calificadores para forzar coincidencias. Los numeros decimales y porcentajes se conservan completos. No usa los descartes del matcher canonico, sinonimos manuales ni nuevas taxonomias. Por ejemplo, `parboil` y `parboilizado` siguen sin considerarse equivalentes automaticamente.
- Rechaza categorias distintas si ambas existen. Categoria ausente no invalida por si sola una descripcion suficiente.
- Presentacion ausente, contradictoria, multiplicadores no resueltos o descripcion vacia tras retirar la marca impiden sugerir.
- No deduce restricciones alimentarias ni certificaciones por similitud vectorial.

## API

### POST /api/v1/decisions/substitutions

Recibe `branch_id`, `items: [{product_id, quantity}]`, `as_of` opcional y `max_price_age_days` (14 por defecto, entre 1 y 90).

Devuelve `branch_id`, `evaluated_at` e `items` para las lineas originales sin precio apto. Cada grupo contiene `original`, `quantity`, `reason` y hasta tres `candidates`, ordenados por subtotal y nombre.

Cada candidato incluye producto, imagen, marca, presentacion normalizada, pack, cantidad de compra, precio unitario, subtotal, moneda, fecha, `price_branch_id`, `inferred_from_chain` y motivo de compatibilidad. La procedencia describe una referencia publicada; no confirma stock fisico.

Cada grupo incluye `diagnostics`: distingue datos originales insuficientes, cadena sin publicaciones activas, ausencia de productos compatibles y productos compatibles sin precio apto. Informa cantidad de compatibles, vencidos, anomalos y dias maximos de vigencia. La interfaz explica la causa real de una lista vacia; no amplia la vigencia ni relaja las reglas silenciosamente.

La recuperacion considera productos y publicaciones activos de la cadena. Chroma puede proponer IDs mediante `ProductSearchIndexPort`, pero todos se filtran contra los productos reales de esa cadena y la misma politica de compatibilidad. Un fallo vectorial genera un warning y no impide las sugerencias estructuradas. Las publicaciones de la cadena se cargan una vez, evitando una consulta de publicaciones por cada candidato.

### POST /api/v1/decisions/ranking

Conserva el contrato anterior y agrega:

```json
{
  "substitutions": [
    {
      "branch_id": "UUID de la sucursal",
      "original_product_id": "UUID de una linea original",
      "replacement_product_id": "UUID del sustituto"
    }
  ]
}
```

Este campo es opcional. Los importes enviados por el navegador no intervienen en el calculo. Se revalidan sucursal, pertenencia de la linea, duplicados, producto activo, compatibilidad y precio apto. Una sustitucion invalida rechaza toda la evaluacion con HTTP 422; `detail.code = invalid_substitution`, `detail.branch_id`, `detail.original_product_id` y `detail.message` identifican el problema. No se elige otro producto silenciosamente.

Resultados completos agregan `basket_type: original | substituted` y `substitutions`, con trazabilidad, cantidades y precios efectivamente utilizados. Los incompletos agregan `distance_km`, `covered_products_count`, `total_products_count` y `substitutions`. Los campos anteriores permanecen.

## Precios y decision

`decision/application/branch_prices.py` comparte la politica existente de vigencia, anomalias, prioridad del precio propio y referencia por cadena entre sugerencias y ranking.

Cada sucursal recibe su canasta efectiva en memoria. El total suma todas las lineas originales con sus cantidades, incluso si varias apuntan al mismo reemplazo. Se conserva el detalle separado para poder explicar cada cambio. Los faltantes no resueltos siguen excluyendo esa sucursal.

Se mantiene el WSM y sus pesos. El ahorro se calcula respecto de la alternativa completa mas costosa de esa evaluacion; puede incluir canastas con sustituciones aceptadas y esto se informa en pantalla. Quitar las sustituciones restaura la evaluacion de la lista original.

## Estado de interfaz

- Las selecciones viven en `useSubstitutions`, fuera de Pinia persistido/localStorage.
- Productos, cantidades o ciudad: eliminan selecciones, sugerencias y ranking.
- Pesos u origen: invalidan el ranking y conservan selecciones.
- Actualizacion de precios: invalida sugerencias y ranking, conserva selecciones para revalidarlas al recalcular.
- Identificadores de solicitud y generaciones descartan respuestas tardias de ranking, precios y sugerencias.
- Los errores no ocultan los controles. Se puede cambiar, quitar o restaurar un reemplazo y volver a calcular.
- La cobertura del panel se etiqueta como la ultima evaluacion; cambiar una seleccion no implica que un nuevo precio haya sido validado hasta recalcular.

## Verificacion

Desde `backend`: `uv run pytest -q`.

Desde `frontend`: `npm test` y `npm run build`.

Los tests HTTP usan SQLite temporal con repositorios reales y un indice que falla deliberadamente. No consultan scrapers, PostgreSQL de produccion ni descargan el modelo. Cubren compatibilidad, referencias por cadena, prioridad directa, cantidades acumuladas, sustituciones manipuladas y cambios entre sugerencia y aceptacion.

Para auditar la base configurada sin modificarla: `uv run python scripts/diagnose_product_substitutions.py --query arroz`. Resume cobertura de precios por cadena, pares aptos y firmas estructuradas. Usa las mismas reglas que el buscador de sustitutos y no consulta Chroma ni scrapers.

El modo mock incluye el producto adicional **Leche Entera SanCor 1 L**. En Comodoro falta en La Anonima y se ofrece Leche Entera 1 L de otra marca. Permite probar seleccion, recalculo y restauracion sin datos externos. La disponibilidad de este escenario es ficticia y no representa inventario real.
