<script setup lang="ts">
import { ref, watch } from 'vue'
import { ImageOff } from 'lucide-vue-next'

const props = defineProps<{ src?: string | null; name: string; large?: boolean }>()
const failed = ref(false)
watch(() => props.src, () => { failed.value = false })
</script>

<template>
  <div class="grid shrink-0 place-items-center overflow-hidden rounded-lg border border-slate-100 bg-white" :class="large ? 'h-64 w-full sm:h-80' : 'size-14'">
    <img v-if="src && !failed" :key="src" :src="src" :alt="name" width="56" height="56"
      loading="lazy" decoding="async" referrerpolicy="no-referrer"
      class="size-full min-h-0 min-w-0 object-contain p-1" @error="failed = true" />
    <span v-else class="grid size-full place-items-center text-slate-400" role="img"
      :aria-label="`Imagen no disponible: ${name}`" title="Imagen no disponible">
      <ImageOff class="size-5" aria-hidden="true" />
    </span>
  </div>
</template>
