<script setup lang="ts">
import {
  ArrowRight,
  BadgeCheck,
  BarChart3,
  Check,
  CircleDollarSign,
  MapPinned,
  Menu,
  PackageCheck,
  ShoppingBasket,
  Sparkles,
} from 'lucide-vue-next'

const supermarkets = ['La Anónima', 'Carrefour', 'Chango Más', 'Jumbo', 'Maxiconsumo']

const basketPreview = ['Coca Cola 2.25 L', 'Leche Entera 1 L', 'Arroz Largo Fino 1 Kg']

const steps = [
  {
    icon: ShoppingBasket,
    title: 'Armá tu canasta',
    text: 'Buscá los productos que necesitás y definí cantidades.',
  },
  {
    icon: MapPinned,
    title: 'Elegí tu ciudad',
    text: 'Tomamos una ciudad de referencia para estimar distancias.',
  },
  {
    icon: BarChart3,
    title: 'Compará y decidí',
    text: 'El ranking combina precio, cercanía y ahorro.',
  },
]

const benefits = [
  {
    icon: CircleDollarSign,
    title: 'Precio total',
    text: 'Calculamos el costo de toda tu canasta, no solo de un producto.',
  },
  {
    icon: MapPinned,
    title: 'Distancia',
    text: 'La distancia se calcula desde la ciudad que elegiste.',
  },
  {
    icon: BadgeCheck,
    title: 'Ahorro visible',
    text: 'Mostramos cuánto ahorrás frente a la alternativa más cara.',
  },
]

const metrics = [
  { value: '5', label: 'productos de prueba' },
  { value: '4', label: 'supermercados' },
  { value: '4', label: 'sucursales' },
  { value: 'ARS', label: 'moneda utilizada' },
]
</script>

<template>
  <main class="relative isolate overflow-hidden bg-[#a8c9e7] text-slate-950">
    <div class="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden="true">
      <div class="absolute -left-24 top-20 size-72 rounded-full bg-white/30 blur-3xl motion-safe:animate-drift" />
      <div class="absolute -right-24 top-56 size-80 rounded-full bg-sky-300/45 blur-3xl motion-safe:animate-drift [animation-delay:-4s]" />
      <div class="absolute inset-x-0 top-0 h-[38rem] bg-[linear-gradient(180deg,rgba(255,255,255,0.34),transparent)]" />
    </div>

    <header class="mx-auto w-full max-w-6xl px-4 pt-5 sm:px-6 lg:px-8 lg:pt-10">
      <div class="glass-card grid grid-cols-[auto_1fr_auto] items-center gap-4 rounded-2xl px-4 py-3 sm:px-6">
        <RouterLink to="/" class="flex items-center gap-2.5 text-lg font-bold tracking-tight">
          <span class="grid size-8 place-items-center rounded-xl bg-slate-950 text-white"><Sparkles class="size-4" /></span>
          <span>DSS Precios</span>
        </RouterLink>
        <nav class="hidden justify-center gap-7 text-sm font-medium text-slate-600 md:flex" aria-label="Principal">
          <a href="#como-funciona" class="transition hover:text-slate-950">Cómo funciona</a>
          <RouterLink to="/datos" class="transition hover:text-slate-950">Datos</RouterLink>
          <a href="#beneficios" class="transition hover:text-slate-950">Beneficios</a>
        </nav>
        <RouterLink to="/comparar" class="hidden rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-slate-950/15 transition hover:-translate-y-0.5 hover:bg-slate-800 sm:inline-flex">
          Probar ahora
        </RouterLink>
        <RouterLink to="/comparar" class="grid size-9 place-items-center rounded-xl bg-slate-900 text-white sm:hidden" aria-label="Probar comparador">
          <Menu class="size-5" />
        </RouterLink>
      </div>
    </header>

    <section class="mx-auto max-w-6xl px-4 pb-20 pt-20 text-center sm:px-6 sm:pt-28 lg:px-8 lg:pb-28">
      <span v-reveal class="inline-flex items-center gap-2 rounded-full border border-slate-900/10 bg-white/25 px-3 py-1.5 text-xs font-semibold text-slate-700 backdrop-blur">
        <span class="size-1.5 rounded-full bg-amber-400" />
        Decisiones de compra basadas en datos
      </span>
      <h1 v-reveal="{ delay: 80 }" class="mx-auto mt-6 max-w-4xl text-5xl font-semibold tracking-[-0.055em] text-slate-950 sm:text-6xl lg:text-8xl">
        Tu canasta,<br />la mejor decisión.
      </h1>
      <p v-reveal="{ delay: 160 }" class="mx-auto mt-6 max-w-2xl text-base leading-7 text-slate-700 sm:text-lg">
        Compará precios, distancia y ahorro entre supermercados y descubrí dónde te conviene comprar hoy.
      </p>
      <div v-reveal="{ delay: 240 }" class="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
        <RouterLink to="/comparar" class="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl bg-white px-6 py-3 font-semibold text-slate-900 shadow-float transition hover:-translate-y-0.5 hover:bg-slate-50">
          Comparar mi canasta <ArrowRight class="size-4" />
        </RouterLink>
        <RouterLink to="/datos" class="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl px-5 py-3 font-semibold text-slate-800 transition hover:bg-white/25">
          Ver datos de prueba <ArrowRight class="size-4" />
        </RouterLink>
      </div>

      <div v-reveal="{ delay: 320 }" class="relative mx-auto mt-16 max-w-5xl text-left sm:mt-20">
        <div class="absolute -inset-x-8 -bottom-10 h-40 rounded-[50%] bg-white/35 blur-3xl" aria-hidden="true" />
        <div class="relative overflow-hidden rounded-3xl border border-white/80 bg-white/72 p-3 shadow-float backdrop-blur-xl sm:p-5">
          <div class="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
            <section class="rounded-2xl border border-slate-100 bg-white p-5 sm:p-6">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-semibold text-slate-900">Comparación de la canasta</p>
                  <p class="mt-1 text-xs text-slate-500">Comodoro Rivadavia · Datos de ejemplo</p>
                </div>
                <span class="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">Mejor opción</span>
              </div>
              <div class="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <article class="rounded-2xl border border-emerald-100 bg-emerald-50/55 p-4 sm:col-span-2">
                  <div class="flex items-center justify-between gap-3">
                    <div class="flex items-center gap-3">
                      <span class="grid size-9 place-items-center rounded-xl bg-emerald-600 text-white"><ShoppingBasket class="size-4" /></span>
                      <div><p class="font-semibold">Chango Más</p><p class="text-xs text-slate-500">Sucursal Comodoro</p></div>
                    </div>
                    <strong class="text-lg tracking-tight">$10.020</strong>
                  </div>
                  <div class="mt-4 h-2 overflow-hidden rounded-full bg-emerald-100"><div class="h-full w-[92%] rounded-full bg-emerald-500" /></div>
                  <p class="mt-2 text-xs font-medium text-emerald-700">Puntaje de conveniencia: 95%</p>
                </article>
                <article class="rounded-2xl bg-slate-950 p-4 text-white">
                  <p class="text-xs font-medium text-slate-300">Ahorro estimado</p>
                  <p class="mt-2 text-2xl font-semibold tracking-tight">$660</p>
                  <p class="mt-1 text-xs text-emerald-300">frente a la opción más cara</p>
                </article>
              </div>
              <div class="mt-4 grid grid-cols-2 gap-3 text-sm text-slate-600 sm:grid-cols-4">
                <div class="rounded-xl bg-slate-50 p-3"><p class="text-xs text-slate-400">Productos</p><p class="mt-1 font-semibold text-slate-800">5 productos</p></div>
                <div class="rounded-xl bg-slate-50 p-3"><p class="text-xs text-slate-400">Distancia</p><p class="mt-1 font-semibold text-slate-800">2,0 km</p></div>
                <div class="rounded-xl bg-slate-50 p-3"><p class="text-xs text-slate-400">Precio</p><p class="mt-1 font-semibold text-slate-800">60%</p></div>
                <div class="rounded-xl bg-slate-50 p-3"><p class="text-xs text-slate-400">Ahorro</p><p class="mt-1 font-semibold text-slate-800">10%</p></div>
              </div>
            </section>
            <aside class="rounded-2xl bg-slate-950 p-5 text-white sm:p-6">
              <div class="flex items-center gap-2 text-sm font-semibold"><PackageCheck class="size-4 text-sky-300" /> Tu canasta</div>
              <ul class="mt-5 space-y-3 text-sm">
                <li v-for="item in basketPreview" :key="item" class="flex items-center justify-between border-b border-white/10 pb-3">
                  <span class="text-slate-200">{{ item }}</span><Check class="size-4 text-emerald-300" />
                </li>
              </ul>
              <RouterLink to="/comparar" class="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-sky-300 px-4 py-3 text-sm font-bold text-slate-950 transition hover:bg-sky-200">Armar canasta <ArrowRight class="size-4" /></RouterLink>
            </aside>
          </div>
        </div>
      </div>
    </section>
  </main>

  <section class="bg-white py-10">
    <div v-reveal class="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-10 gap-y-4 px-4 text-sm font-bold tracking-tight text-slate-400 sm:px-6 lg:px-8">
      <span class="mr-2 text-xs font-medium uppercase tracking-[0.16em] text-slate-400">Datos de referencia</span>
      <span v-for="supermarket in supermarkets" :key="supermarket">{{ supermarket }}</span>
    </div>
  </section>

  <section id="como-funciona" class="bg-slate-50 py-20 sm:py-28">
    <div class="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
      <div v-reveal class="max-w-2xl">
        <span class="section-kicker">Simple y transparente</span>
        <h2 class="mt-5 text-3xl font-semibold tracking-tight sm:text-4xl">Decidir bien no debería llevarte horas.</h2>
      </div>
      <div class="mt-12 grid grid-cols-1 gap-5 md:grid-cols-3">
        <article v-for="(step, index) in steps" :key="step.title" v-reveal="{ delay: index * 90 }" class="rounded-3xl border border-slate-100 bg-white p-6 shadow-sm">
          <span class="text-sm font-bold text-sky-600">0{{ index + 1 }}</span>
          <component :is="step.icon" class="mt-8 size-6 text-slate-900" />
          <h3 class="mt-5 text-lg font-semibold">{{ step.title }}</h3>
          <p class="mt-2 leading-6 text-slate-500">{{ step.text }}</p>
        </article>
      </div>
    </div>
  </section>

  <section id="beneficios" class="bg-white py-20 sm:py-28">
    <div class="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
      <div v-reveal class="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:items-end">
        <div>
          <span class="section-kicker">Lo que miramos</span>
          <h2 class="mt-5 text-3xl font-semibold tracking-tight sm:text-4xl">Un ranking que muestra el porqué de cada recomendación.</h2>
        </div>
        <p class="max-w-xl leading-7 text-slate-500">Podés ajustar el peso de cada criterio antes de comparar. El resultado es transparente: cada alternativa muestra los datos que explican la recomendación.</p>
      </div>
      <div class="mt-12 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
        <article v-for="(item, index) in benefits" :key="item.title" v-reveal="{ delay: index * 90 }" class="rounded-3xl bg-slate-50 p-6">
          <component :is="item.icon" class="size-6 text-emerald-600" />
          <h3 class="mt-6 font-semibold">{{ item.title }}</h3>
          <p class="mt-2 leading-6 text-slate-500">{{ item.text }}</p>
        </article>
      </div>
      <div class="mt-16 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div v-for="(metric, index) in metrics" :key="metric.label" v-reveal="{ delay: index * 70 }" class="rounded-2xl border border-slate-100 p-5 text-center">
          <p class="text-2xl font-semibold tracking-tight">{{ metric.value }}</p>
          <p class="mt-1 text-sm text-slate-500">{{ metric.label }}</p>
        </div>
      </div>
    </div>
  </section>

  <section class="bg-slate-950 py-20 text-white sm:py-24">
    <div v-reveal class="mx-auto grid max-w-6xl grid-cols-1 gap-8 px-4 sm:px-6 lg:grid-cols-[1fr_auto] lg:items-center lg:px-8">
      <div>
        <p class="text-sm font-semibold text-sky-300">Listo cuando vos lo estés</p>
        <h2 class="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">Probá el ranking con la canasta que quieras.</h2>
      </div>
      <RouterLink to="/comparar" class="inline-flex items-center justify-center gap-2 rounded-2xl bg-sky-300 px-6 py-3.5 font-bold text-slate-950 transition hover:bg-sky-200">Empezar a comparar <ArrowRight class="size-4" /></RouterLink>
    </div>
  </section>

  <footer class="bg-slate-950 px-4 pb-8 text-sm text-slate-400 sm:px-6 lg:px-8">
    <div class="mx-auto flex max-w-6xl flex-col justify-between gap-3 border-t border-white/10 pt-6 sm:flex-row">
      <p>© 2026 DSS Precios. Datos de prueba para uso académico.</p>
      <RouterLink to="/datos" class="transition hover:text-white">Explorar datos de prueba</RouterLink>
    </div>
  </footer>
</template>
