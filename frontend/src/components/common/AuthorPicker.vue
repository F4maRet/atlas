<template>
  <div class="author-picker">
    <div class="selected-authors">
      <span v-for="(a, i) in selectedAuthors" :key="a.id" class="tag" :title="a.full_name">
        <span v-if="numbered" class="tag__num">{{ i + 1 }}</span>
        {{ a.full_name }}
        <button v-if="i > 0" type="button" class="tag__btn" title="Сдвинуть выше" @click="moveUp(i)">↑</button>
        <button type="button" class="tag__btn" title="Убрать" @click="remove(a.id)">✕</button>
      </span>
      <span v-if="!selectedAuthors.length" class="text-muted text-sm">{{ emptyText }}</span>
    </div>
    <div class="author-search">
      <input
        v-model="query"
        class="input"
        :placeholder="placeholder"
        role="combobox"
        :aria-expanded="open"
        @focus="open = true"
        @blur="onBlur"
        @keydown.down.prevent="move(1)"
        @keydown.up.prevent="move(-1)"
        @keydown.enter.prevent="choose"
        @keydown.esc.stop="open = false"
      />
      <div v-if="open && (filtered.length || canCreate)" class="author-dropdown" role="listbox">
        <div
          v-for="(a, i) in filtered"
          :key="a.id"
          class="author-dropdown__item"
          :class="{ active: i === cursor }"
          role="option"
          @mousedown.prevent="add(a)"
          @mouseenter="cursor = i"
        >
          {{ a.full_name }}
          <span v-if="a.organization" class="text-muted text-sm"> · {{ a.organization }}</span>
        </div>
        <div
          v-if="canCreate"
          class="author-dropdown__item author-dropdown__create"
          :class="{ active: cursor === filtered.length }"
          @mousedown.prevent="createNew"
          @mouseenter="cursor = filtered.length"
        >
          + Добавить в справочник «{{ query.trim() }}»
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useToast } from 'vue-toastification'
import { authorsApi } from '@/utils/api'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  allAuthors: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Начните вводить ФИО…' },
  emptyText: { type: String, default: 'Авторы не выбраны' },
  numbered: { type: Boolean, default: true },
})
const emit = defineEmits(['update:modelValue', 'created'])
const toast = useToast()

const query = ref('')
const open = ref(false)
const cursor = ref(0)

const byId = computed(() => new Map(props.allAuthors.map(a => [a.id, a])))
// Порядок — как выбран пользователем (первый автор важен для заключений и отчётов)
const selectedAuthors = computed(() => props.modelValue.map(id => byId.value.get(id)).filter(Boolean))

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  return props.allAuthors
    .filter(a => !props.modelValue.includes(a.id))
    .filter(a => !q || a.full_name.toLowerCase().includes(q) || (a.short_name || '').toLowerCase().includes(q))
    .slice(0, 8)
})
const canCreate = computed(() => {
  const q = query.value.trim().toLowerCase()
  return q.length > 2 && !props.allAuthors.some(a => a.full_name.toLowerCase() === q)
})

watch(query, () => { cursor.value = 0; open.value = true })

function onBlur() { setTimeout(() => { open.value = false }, 120) }
function move(d) {
  const max = filtered.value.length + (canCreate.value ? 1 : 0)
  if (!max) return
  open.value = true
  cursor.value = (cursor.value + d + max) % max
}
function choose() {
  if (cursor.value < filtered.value.length) add(filtered.value[cursor.value])
  else if (canCreate.value) createNew()
}
function add(author) {
  if (!props.modelValue.includes(author.id)) emit('update:modelValue', [...props.modelValue, author.id])
  query.value = ''
}
function remove(id) {
  emit('update:modelValue', props.modelValue.filter(x => x !== id))
}
function moveUp(i) {
  const ids = [...props.modelValue]
  ;[ids[i - 1], ids[i]] = [ids[i], ids[i - 1]]
  emit('update:modelValue', ids)
}
async function createNew() {
  const name = query.value.trim()
  if (!name) return
  try {
    const res = await authorsApi.create({ full_name: name })
    if (!byId.value.has(res.data.id)) emit('created', res.data)
    add(res.data)
  } catch (e) {
    toast.error(e.message)
  }
}
</script>

<style scoped>
.author-picker { display: flex; flex-direction: column; gap: 8px; }
.selected-authors { display: flex; flex-wrap: wrap; gap: 6px; min-height: 28px; align-items: center; }
.tag__num { font-size: 10px; color: var(--c-text3); font-weight: 700; }
.tag__btn { background: none; border: none; cursor: pointer; color: var(--c-text3); font-size: 11px; padding: 0 2px; }
.tag__btn:hover { color: var(--c-text); }
.author-search { position: relative; }
.author-dropdown {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 100;
  background: var(--c-bg2); border: 1px solid var(--c-border2);
  border-radius: var(--radius); margin-top: 4px;
  max-height: 240px; overflow-y: auto; box-shadow: var(--shadow);
}
.author-dropdown__item { padding: 8px 12px; cursor: pointer; font-size: 13px; }
.author-dropdown__item.active { background: var(--c-surface); }
.author-dropdown__create { color: var(--c-accent); border-top: 1px solid var(--c-border); }
</style>
