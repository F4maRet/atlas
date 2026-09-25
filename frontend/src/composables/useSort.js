import { ref, computed, unref } from 'vue'

const collator = new Intl.Collator('ru', { numeric: true, sensitivity: 'base' })

/**
 * Сортировка списка по клику на заголовок таблицы.
 * getters: { key: item => value } — как получить значение для колонки.
 */
export function useSort(list, getters, initial = { key: null, dir: 'desc' }) {
  const sortKey = ref(initial.key)
  const sortDir = ref(initial.dir)

  function toggle(key) {
    if (sortKey.value === key) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
    else { sortKey.value = key; sortDir.value = 'asc' }
  }

  const sorted = computed(() => {
    const items = [...(unref(list) || [])]
    const get = getters[sortKey.value]
    if (!get) return items
    const k = sortDir.value === 'asc' ? 1 : -1
    return items.sort((a, b) => {
      const va = get(a), vb = get(b)
      if (va == null || va === '') return 1
      if (vb == null || vb === '') return -1
      if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * k
      return collator.compare(String(va), String(vb)) * k
    })
  })

  return { sortKey, sortDir, toggle, sorted }
}
