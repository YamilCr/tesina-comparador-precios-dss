import type { SubstitutionDiagnostics } from '@/types'

export function substitutionEmptyMessage(diagnostics?: SubstitutionDiagnostics): string {
  switch (diagnostics?.code) {
    case 'insufficient_attributes':
      return 'Los datos de este producto no permiten verificar su presentación o tipo. No se pueden proponer reemplazos seguros.'
    case 'no_chain_products':
      return 'Esta cadena no tiene publicaciones activas de productos cargadas.'
    case 'no_compatible_products':
      return 'Ningún producto cargado de esta cadena cumple las reglas de igual tipo, variantes, cantidad y pack. Se admiten diferencias menores de escritura, pero no omitir calificadores o restricciones.'
    case 'no_suitable_prices': {
      const count = diagnostics.compatible_products
      const reasons: string[] = []
      if (diagnostics.stale_products) reasons.push(`${diagnostics.stale_products} con precios de más de ${diagnostics.max_price_age_days} días`)
      if (diagnostics.suspect_products) reasons.push(`${diagnostics.suspect_products} con precios anómalos`)
      const missing = count - diagnostics.stale_products - diagnostics.suspect_products
      if (missing > 0) reasons.push(`${missing} sin precio disponible`)
      return `${count === 1 ? 'Hay 1 producto compatible' : `Hay ${count} productos compatibles`}, pero no ${count === 1 ? 'tiene' : 'tienen'} precios aptos: ${reasons.join('; ')}. Se necesitan precios actualizados y válidos para incluirlos.`
    }
    default:
      return 'No hay alternativas compatibles con precio apto.'
  }
}
