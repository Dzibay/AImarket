// v-reveal — плавное появление элемента при прокрутке.
// v-reveal="120" задаёт задержку в мс (удобно для каскада карточек).
let observer = null

function getObserver() {
  if (observer || typeof IntersectionObserver === 'undefined') return observer
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue
        entry.target.classList.add('is-in')
        observer.unobserve(entry.target)
      }
    },
    { rootMargin: '0px 0px -8% 0px', threshold: 0.08 },
  )
  return observer
}

export const reveal = {
  mounted(el, binding) {
    const io = getObserver()
    if (!io) return
    el.classList.add('reveal')
    if (binding.value) el.style.setProperty('--reveal-delay', `${Number(binding.value)}ms`)
    io.observe(el)
  },
  unmounted(el) {
    observer?.unobserve(el)
  },
}
