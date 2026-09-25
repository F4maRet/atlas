import { watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/**
 * Если в адресе есть ?open=<id> (переход из глобального поиска или дашборда),
 * открыть карточку записи, как только список загрузится, и убрать параметр.
 * ?new=1 (быстрые кнопки дашборда) — сразу открыть форму создания.
 */
export function useOpenFromQuery(items, open, create) {
  const route = useRoute()
  const router = useRouter()
  if (create) {
    watch(() => route.query.new, v => {
      if (!v) return
      create()
      const { new: _omit, ...rest } = route.query
      router.replace({ query: rest })
    }, { immediate: true })
  }
  watch(
    () => [route.query.open, items.value.length],
    () => {
      const id = Number(route.query.open)
      if (!id || !items.value.length) return
      const item = items.value.find(x => x.id === id)
      if (item) {
        open(item)
        const { open: _omit, ...rest } = route.query
        router.replace({ query: rest })
      }
    },
    { immediate: true },
  )
}
