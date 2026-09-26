# Sustituciones de productos por supermercado

## Alcance

El comparador permite completar una canasta con reemplazos elegidos expresamente por el usuario para un supermercado. La lista persistida en el navegador, las identidades canonicas, el ETL y los scrapers no cambian. No hay tablas, migraciones ni dependencias nuevas.

Cada cadena aparece una sola vez en el ranking, el mapa y las canastas incompletas. Entre las sucursales elegibles solicitadas se toma la mas cercana al origen para medir distancia. Las publicaciones activas y los precios aptos de la cadena completan su cobertura, con prioridad del precio de esa sucursal cuando existe. Esto es disponibilidad publicada o inferida, no stock fisico confirmado. Un precio vencido en todas las sucursales no completa la canasta.

Los supermercados incompletos se ordenan por cantidad de productos faltantes y luego por distancia. La interfaz muestra los primeros tres y permite consultar los restantes. No se consideran mas economicos ni participan del ranking mientras tengan faltantes.

## Compatibilidad

`decision/domain/services/substitution_policy.py` es independiente de `ProductIdentityMatcher`. Las sugerencias y su revalidacion usan `similar_product`, que exige una familia reconocible (primera palabra descriptiva, sin marca) y rechaza categorias contradictorias cuando ambas estan informadas. No exige la misma variante, cantidad, unidad ni pack: esas diferencias quedan visibles para eleccion expresa del usuario. No convierte automaticamente la cantidad de envases solicitada, por lo que comparar presentaciones diferentes no implica comparar igual contenido neto.

El matcher conservador `compatible` permanece disponible para validaciones estrictas, pero ya no gobierna las sugerencias de compra:

- Permite cambiar de marca explicitamente informada.
- Exige igualdad de cantidad en unidad base, unidad y pack. Por ejemplo, 1 kg equivale a 1000 g; no se convierte la cantidad de compra ni se reemplazan dos envases chicos por uno grande.
- Compara conjuntos de tokens normalizados del nombre y de la descripcion, si existe. Retira la marca explicita, la presentacion y articulos/conectores neutros. Conserva calificadores como integral, entera, original, sin, gluten, lactosa o azucar.
- Admite plurales regulares, abreviaturas `c/` y `s/`, y como maximo una letra interna omitida/agregada en una palabra larga (al menos ocho letras, mismos tres caracteres iniciales y finales). Usa la distancia Levenshtein de RapidFuzz, ya instalado. Cada palabra debe tener una correspondencia unica; no basta una similitud global alta.
- Puede reconocer ese mismo error de una letra en una marca de una sola palabra, solo si la marca ya esta informada en el producto y no aparece escrita exactamente. No inventa marcas nuevas a partir de palabras desconocidas.
- Para las sustituciones, consulta las marcas activas y puede retirar nombres de marca completos que aparezcan en el titulo aunque falte `brand_id`. Tambien reconoce el alias de una marca compuesta cuando empieza por `Molinos`: `Molinos Ala` puede aparecer como `Ala`. Esto solo afecta a las sugerencias y su revalidacion, no al catalogo canonico.
- Para arroz largo, compara el producto y el tipo `arroz largo`; admite el refinamiento `fino 00000` como alternativa elegida expresamente por el usuario. Mantiene la igualdad de cantidad y pack. No mezcla largo con integral, parboil, doble carolina ni otros tipos.
- Fuera del refinamiento controlado de arroz largo, no omite palabras sobrantes, negaciones ni calificadores para forzar coincidencias. Los numeros decimales y porcentajes se conservan completos. No usa los descartes del matcher canonico ni sinonimos generales; por ejemplo, `parboil` y `parboilizado` siguen sin considerarse equivalentes automaticamente.
- Rechaza categorias distintas si ambas existen. Categoria ausente no invalida por si sola una descripcion suficiente.
- Presentacion ausente, contradictoria, multiplicadores no resueltos o descripcion vacia tras retirar la marca impiden sugerir.
- No deduce restricciones alimentarias ni certificaciones por similitud vectorial.

## API

### POST /api/v1/decisions/substitutions

Recibe `branch_id`, `items: [{product_id, quantity}]`, `as_of` opcional y `max_price_age_days` (14 por defecto, entre 1 y 90).

Devuelve `branch_id`, `evaluated_at` e `items` para las lineas originales sin precio apto. Cada grupo contiene `original`, `quantity`, `reason`, hasta tres `candidates` con precio vigente, hasta dos con ultimo precio vencido, y hasta tres `unpriced_candidates` sin importe utilizable. Dentro de cada grupo con importe, ordena por subtotal y nombre. Las opciones sin precio no quedan ocultas porque existan otras con precio.

Cada candidato incluye producto, imagen, marca, presentacion normalizada, pack, cantidad de compra, precio unitario, subtotal, moneda, fecha, `price_branch_id`, `inferred_from_chain` y motivo de compatibilidad. La procedencia describe una referencia publicada; no confirma stock fisico.

Los `candidates` con `price_status: stale` muestran el ultimo importe y fecha conocidos. Pueden elegirse y participan del ranking como estimacion, con aviso en la opcion y en el resultado. Los `unpriced_candidates` son similares sin importe disponible o con precio anomalo (`missing` o `suspect`): pueden elegirse, pero la cadena sigue como canasta incompleta y sin ahorro calculado hasta tener un precio utilizable. No se inventa un importe.

Cada grupo incluye `diagnostics`: distingue cadena sin publicaciones activas, ausencia de productos de la misma familia y productos similares sin precio utilizable. Informa cantidad de similares, vencidos, anomalos y dias maximos de vigencia. La interfaz explica la causa real de una lista vacia sin inventar importes ni stock.

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

Este campo es opcional. Los importes enviados por el navegador no intervienen en el calculo. Se revalidan sucursal, pertenencia de la linea, duplicados por cadena y producto original, producto activo, familia y publicacion activa en la cadena. El `branch_id` puede ser de cualquier sucursal elegible de la cadena; al recalcular se aplica a la sucursal mas cercana del mismo supermercado. Una sustitucion invalida rechaza toda la evaluacion con HTTP 422; `detail.code = invalid_substitution`, `detail.branch_id`, `detail.original_product_id` y `detail.message` identifican el problema. No se elige otro producto silenciosamente.

Resultados completos agregan `basket_type: original | substituted` y `substitutions`, con trazabilidad, cantidades y precios efectivamente utilizados. Los incompletos agregan `distance_km`, `covered_products_count`, `total_products_count` y `substitutions`. Los campos anteriores permanecen.

## Precios y decision

`decision/application/branch_prices.py` comparte la politica existente de vigencia, anomalias, prioridad del precio propio y referencia por cadena entre sugerencias y ranking. Los precios vencidos se conservan aparte y solo se usan para sustituciones aceptadas, nunca para completar productos originales por defecto. Los importes del ranking que dependen de ellos se marcan estimados; los precios anomalos no entran en el calculo.

Cada supermercado recibe su canasta efectiva en memoria. El total suma todas las lineas originales con sus cantidades, incluso si varias apuntan al mismo reemplazo. Se conserva el detalle separado para poder explicar cada cambio. Los faltantes no resueltos siguen excluyendo ese supermercado.

Se mantiene el WSM y sus pesos. El ahorro se calcula respecto de la alternativa completa mas costosa de esa evaluacion; puede incluir canastas con sustituciones aceptadas y esto se informa en pantalla. Quitar las sustituciones restaura la evaluacion de la lista original.

## Estado de interfaz

- Las selecciones viven en `useSubstitutions`, fuera de Pinia persistido/localStorage.
- Productos, cantidades o ciudad: eliminan selecciones, sugerencias y ranking.
- Pesos u origen: invalidan el ranking y conservan selecciones. Si cambia la sucursal mas cercana, la seleccion sigue asociada a la misma cadena y se revalida con sus precios.
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
