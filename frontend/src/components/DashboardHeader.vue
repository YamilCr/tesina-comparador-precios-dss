<script setup lang="ts">
import { BarChart3, Database, Home, Sparkles } from 'lucide-vue-next'

import { apiMode } from '@/services/api'
</script>

<template>
  <header class="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-5 sm:px-6 lg:px-8">
    <RouterLink to="/" class="group flex items-center gap-3 text-slate-950">
      <span class="grid size-10 place-items-center rounded-2xl bg-slate-950 text-white shadow-float transition group-hover:-translate-y-0.5">
        <Sparkles class="size-5" aria-hidden="true" />
      </span>
      <span class="text-lg font-bold tracking-tight">DSS Precios</span>
    </RouterLink>

    <nav class="hidden items-center gap-1 rounded-2xl border border-white/70 bg-white/65 p-1 shadow-sm backdrop-blur md:flex" aria-label="Principal">
      <RouterLink to="/" class="nav-link"><Home class="size-4" aria-hidden="true" /> Inicio</RouterLink>
      <RouterLink to="/comparar" class="nav-link"><BarChart3 class="size-4" aria-hidden="true" /> Comparar</RouterLink>
      <RouterLink to="/datos" class="nav-link"><Database class="size-4" aria-hidden="true" /> Datos</RouterLink>
    </nav>

    <span
      class="rounded-full border px-3 py-1.5 text-xs font-semibold"
      :class="apiMode === 'mock' ? 'border-sky-200 bg-sky-50 text-sky-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700'"
    >
      {{ apiMode === 'mock' ? 'Demo activa' : 'Backend conectado' }}
    </span>
  </header>
</template>
