import { decorateTitleDuringAlert } from '../composables/useSupportNotify'

export function useHead(title, noindex = false) {
  document.title = decorateTitleDuringAlert(title)
  let robots = document.querySelector('meta[name="robots"]')
  if (noindex) {
    if (!robots) {
      robots = document.createElement('meta')
      robots.name = 'robots'
      document.head.append(robots)
    }
    robots.content = 'noindex'
  } else if (robots) {
    robots.remove()
  }
}
