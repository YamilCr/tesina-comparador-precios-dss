<script setup lang="ts">
import L from 'leaflet'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { IncompleteBranch, RankedBranch, RankingOrigin } from '@/types'

const props = defineProps<{
  origin: RankingOrigin
  ranking: RankedBranch[]
  incomplete: IncompleteBranch[]
}>()

const mapElement = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let markers: L.LayerGroup | null = null

const tooltip = (title: string, detail: string) => {
  const element = document.createElement('div')
  const heading = document.createElement('strong')
  const body = document.createElement('div')
  heading.textContent = title
  body.textContent = detail
  element.append(heading, body)
  return element
}

const renderMarkers = async () => {
  if (!map || !markers) return
  markers.clearLayers()

  const points: L.LatLngExpression[] = []
  const originPoint: L.LatLngExpression = [props.origin.latitud, props.origin.longitud]
  points.push(originPoint)
  L.circleMarker(originPoint, {
    radius: 8,
    color: '#0f172a',
    fillColor: '#38bdf8',
    fillOpacity: 1,
    weight: 3,
  })
    .bindTooltip(tooltip(props.origin.nombre, 'Punto de partida'), { direction: 'top' })
    .addTo(markers)

  props.ranking.forEach((result) => {
    const point: L.LatLngExpression = [result.sucursal.latitud, result.sucursal.longitud]
    points.push(point)
    const recommended = result.posicion === 1
    L.circleMarker(point, {
      radius: recommended ? 10 : 8,
      color: recommended ? '#047857' : '#0369a1',
      fillColor: recommended ? '#34d399' : '#38bdf8',
      fillOpacity: 0.92,
      weight: 3,
    })
      .bindTooltip(
        tooltip(
          `${result.posicion}. ${result.sucursal.supermercado}`,
          `${result.sucursal.nombre} · ${result.distancia_km} km`,
        ),
        { direction: 'top' },
      )
      .addTo(markers!)
  })

  props.incomplete.forEach((result) => {
    const point: L.LatLngExpression = [result.sucursal.latitud, result.sucursal.longitud]
    points.push(point)
    L.circleMarker(point, {
      radius: 7,
      color: '#b45309',
      fillColor: '#fbbf24',
      fillOpacity: 0.82,
      weight: 2,
    })
      .bindTooltip(
        tooltip(result.sucursal.supermercado, `${result.sucursal.nombre} · canasta incompleta`),
        { direction: 'top' },
      )
      .addTo(markers!)
  })

  await nextTick()
  map.invalidateSize()
  if (points.length === 1) map.setView(originPoint, 13)
  else map.fitBounds(L.latLngBounds(points), { padding: [36, 36], maxZoom: 14 })
}

onMounted(() => {
  if (!mapElement.value) return
  map = L.map(mapElement.value, { scrollWheelZoom: false, zoomControl: true })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map)
  markers = L.layerGroup().addTo(map)
  void renderMarkers()
})

watch(
  () => [props.origin, props.ranking, props.incomplete],
  () => void renderMarkers(),
  { deep: true },
)

onBeforeUnmount(() => {
  map?.remove()
  map = null
  markers = null
})
</script>

<template>
  <div
    ref="mapElement"
    class="h-80 w-full overflow-hidden rounded-lg border border-slate-200 bg-slate-100 shadow-sm sm:h-96"
    role="img"
    aria-label="Mapa del origen y las sucursales comparadas"
  />
</template>
