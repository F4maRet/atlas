<template>
  <div>
    <div class="author-picker">
      <div class="selected-authors">
        <span v-for="a in selectedAuthors" :key="a.id" class="tag">
          {{ a.full_name }}
          <button @click="remove(a.id)" style="background:none;border:none;cursor:pointer;color:var(--c-text2);font-size:12px;padding:0 2px">✕</button>
        </span>
        <span v-if="!selectedAuthors.length" class="text-muted text-sm">Авторы не выбраны</span>
      </div>
      <div class="author-search">
        <input
          class="input"
          v-model="query"
          placeholder="Добавить автора..."
          @focus="showDropdown = true"
          @blur="setTimeout(() => showDropdown = false, 200)"
        />
        <div v-if="showDropdown && filtered.length" class="author-dropdown">
          <div
            v-for="a in filtered"
            :key="a.id"
            class="author-dropdown__item"
            @mousedown.prevent="add(a)"
          >
            {{ a.full_name }}
            <span v-if="a.organization" class="text-muted text-sm"> · {{ a.organization }}</span>
          </div>
        </div>
        <div v-if="showDropdown && query && !filtered.length" class="author-dropdown">
          <div class="author-dropdown__item" @mousedown.prevent="createNew">
            <span style="color:var(--c-accent)">+ Создать «{{ query }}»</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { authorsApi } from '@/utils/api'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  allAuthors: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue', 'created'])

const query = ref('')
const showDropdown = ref(false)

const selectedAuthors = computed(() =>
  props.allAuthors.filter(a => props.modelValue.includes(a.id))
)

const filtered = computed(() =>
  props.allAuthors
    .filter(a => !props.modelValue.includes(a.id))
    .filter(a => a.full_name.toLowerCase().includes(query.value.toLowerCase()))
    .slice(0, 8)
)

function add(author) {
  if (!props.modelValue.includes(author.id)) {
    emit('update:modelValue', [...props.modelValue, author.id])
  }
  query.value = ''
}
function remove(id) {
  emit('update:modelValue', props.modelValue.filter(x => x !== id))
}
async function createNew() {
  try {
    const res = await authorsApi.create({ full_name: query.value.trim() })
    emit('created', res.data)
    add(res.data)
  } catch (e) { console.error(e) }
  query.value = ''
}
</script>

<style scoped>
.author-picker { display: flex; flex-direction: column; gap: 8px; }
.selected-authors { display: flex; flex-wrap: wrap; gap: 6px; min-height: 28px; }
.author-search { position: relative; }
.author-dropdown {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 100;
  background: var(--c-bg2); border: 1px solid var(--c-border2);
  border-radius: var(--radius); margin-top: 4px;
  max-height: 200px; overflow-y: auto;
  box-shadow: var(--shadow);
}
.author-dropdown__item {
  padding: 8px 12px; cursor: pointer; font-size: 13px;
  transition: background 0.1s;
}
.author-dropdown__item:hover { background: var(--c-surface); }
</style>
