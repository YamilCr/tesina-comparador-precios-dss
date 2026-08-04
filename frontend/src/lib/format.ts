export const formatCurrency = (value: string | number) =>
  new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    maximumFractionDigits: 0,
  }).format(Number(value))

export const formatNumber = (value: string | number, maximumFractionDigits = 1) =>
  new Intl.NumberFormat('es-AR', { maximumFractionDigits }).format(Number(value))

export const formatDate = (value: string | null) => {
  if (!value) return 'Sin relevamiento'
  return new Intl.DateTimeFormat('es-AR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value))
}
