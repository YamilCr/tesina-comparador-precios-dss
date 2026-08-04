import type { Directive } from 'vue'

type RevealBinding =
  | number
  | {
      delay?: number
      once?: boolean
    }
  | undefined

type RevealOptions = {
  delay: number
  once: boolean
}

const observedElements = new WeakMap<HTMLElement, RevealOptions>()

let observer: IntersectionObserver | null = null

function shouldReduceMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function normalizeOptions(value: RevealBinding): RevealOptions {
  if (typeof value === 'number') {
    return { delay: value, once: true }
  }

  return {
    delay: value?.delay ?? 0,
    once: value?.once ?? true,
  }
}

function getObserver() {
  if (observer) {
    return observer
  }

  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        const element = entry.target as HTMLElement
        const options = observedElements.get(element)

        if (entry.isIntersecting) {
          element.classList.add('is-revealed')

          if (options?.once !== false) {
            observer?.unobserve(element)
            observedElements.delete(element)
          }
        } else if (options?.once === false) {
          element.classList.remove('is-revealed')
        }
      })
    },
    {
      rootMargin: '0px 0px -10% 0px',
      threshold: 0.14,
    },
  )

  return observer
}

export const revealDirective: Directive<HTMLElement, RevealBinding> = {
  mounted(element, binding) {
    const options = normalizeOptions(binding.value)

    element.classList.add('reveal-on-scroll')
    element.style.setProperty('--reveal-delay', `${options.delay}ms`)

    if (!('IntersectionObserver' in window) || shouldReduceMotion()) {
      element.classList.add('is-revealed')
      return
    }

    observedElements.set(element, options)
    getObserver().observe(element)
  },

  updated(element, binding) {
    const options = normalizeOptions(binding.value)
    element.style.setProperty('--reveal-delay', `${options.delay}ms`)
    observedElements.set(element, options)
  },

  unmounted(element) {
    observer?.unobserve(element)
    observedElements.delete(element)
  },
}
