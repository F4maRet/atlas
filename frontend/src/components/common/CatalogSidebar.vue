<template>
  <aside class="catalog-sidebar" @click="menu.visible = false">
    <div class="catalog-sidebar__head">
      <span class="catalog-sidebar__title">📁 Каталоги</span>
      <button class="btn btn-ghost btn-sm btn-icon" title="Новый каталог" @click.stop="startCreate">＋</button>
    </div>

    <form v-if="creating" class="catalog-new" @submit.prevent="confirmCreate" @click.stop>
      <input ref="createInput" v-model="newName" class="input input-sm" placeholder="Название каталога"
        maxlength="500" @keydown.esc="creating = false" />
      <div class="flex gap-2 mt-2">
        <button class="btn btn-primary btn-sm" type="submit">Создать</button>
        <button class="btn btn-secondary btn-sm" type="button" @click="creating = false">Отмена</button>
      </div>
    </form>

    <div
      v-for="item in fixedItems" :key="item.key"
      class="catalog-item" :class="{ active: modelValue === item.value, 'drop-target': dragOver === item.key }"
      @click="$emit('update:modelValue', item.value)"
      @dragover.prevent="dragOver = item.key" @dragleave="dragOver = null"
      @drop.prevent="onDrop(item.key === 'all' ? undefined : null, $event)"
    >
      <span class="catalog-item__icon">{{ item.icon }}</span>
      <span class="catalog-item__name">{{ item.label }}</span>
      <span class="catalog-item__count">{{ item.count }}</span>
    </div>

    <div class="catalog-list">
      <div
        v-for="cat in catalogs" :key="cat.name"
        class="catalog-item" :class="{ active: modelValue === cat.name, 'drop-target': dragOver === cat.name }"
        :title="cat.name"
        @click="$emit('update:modelValue', cat.name)"
        @contextmenu.prevent.stop="openMenu(cat.name, $event)"
        @dragover.prevent="dragOver = cat.name" @dragleave="dragOver = null"
        @drop.prevent="onDrop(cat.name, $event)"
      >
        <span class="catalog-item__icon">📁</span>
        <form v-if="renaming === cat.name" class="catalog-rename" @submit.prevent="confirmRename(cat.name)" @click.stop>
          <input ref="renameInput" v-model="renameValue" class="input input-sm" maxlength="500"
            @keydown.esc="renaming = null" @blur="confirmRename(cat.name)" />
        </form>
        <span v-else class="catalog-item__name">{{ cat.name }}</span>
        <span class="catalog-item__count">{{ counts[cat.name] ?? 0 }}</span>
        <button class="catalog-item__more" title="Действия" @click.stop="openMenu(cat.name, $event)">⋯</button>
      </div>
    </div>
    <div v-if="catalogs.length" class="catalog-hint">Перетащите строку таблицы на каталог, чтобы переместить её</div>

    <Teleport to="body">
      <div v-if="menu.visible" class="context-menu" :style="{ top: menu.y + 'px', left: menu.x + 'px' }" @click.stop>
        <div class="context-menu__item" @click="startRename(menu.name)">✏️ Переименовать</div>
        <div class="context-menu__item" @click="startCreate">📁 Новый каталог</div>
        <div class="context-menu__divider"></div>
        <div class="context-menu__item context-menu__item--danger" @click="remove(menu.name)">🗑 Удалить каталог</div>
      </div>
    </Teleport>
  </aside>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useToast } from 'vue-toastification'
import { catalogsApi } from '@/utils/api'
import { confirmDialog } from '@/composables/useConfirm'

const props = defineProps({
  scope: { type: String, required: true }, // articles | proposals | software
  items: { type: Array, default: () => [] }, // записи раздела (для счётчиков)
  modelValue: { type: String, default: '' }, // '' — все, '__none__' — без каталога, иначе имя
  allLabel: { type: String, default: 'Все записи' },
})
const emit = defineEmits(['update:modelValue', 'changed'])
const toast = useToast()

const catalogs = ref([])
const creating = ref(false)
const newName = ref('')
const createInput = ref(null)
const renaming = ref(null)
const renameValue = ref('')
const renameInput = ref(null)
const dragOver = ref(null)
const menu = ref({ visible: false, x: 0, y: 0, name: '' })

const counts = computed(() => {
  const m = {}
  for (const it of props.items) if (it.catalog) m[it.catalog] = (m[it.catalog] || 0) + 1
  return m
})
const fixedItems = computed(() => [
  { key: 'all', value: '', icon: '📋', label: props.allLabel, count: props.items.length },
  { key: 'none', value: '__none__', icon: '📂', label: 'Без каталога', count: props.items.filter(i => !i.catalog).length },
])

async function reload() {
  try {
    const { data } = await catalogsApi.list(props.scope)
    catalogs.value = data
  } catch (e) { toast.error(e.message) }
}
defineExpose({ reload, catalogs })

function startCreate() {
  menu.value.visible = false
  creating.value = true
  newName.value = ''
  nextTick(() => createInput.value?.focus())
}
async function confirmCreate() {
  const name = newName.value.trim()
  creating.value = false
  if (!name) return
  try {
    await catalogsApi.create(props.scope, name)
    await reload()
    emit('update:modelValue', name)
  } catch (e) { toast.error(e.message) }
}

function startRename(name) {
  menu.value.visible = false
  renaming.value = name
  renameValue.value = name
  nextTick(() => { const el = [].concat(renameInput.value)[0]; el?.focus(); el?.select() })
}
async function confirmRename(oldName) {
  if (renaming.value !== oldName) return
  const name = renameValue.value.trim()
  renaming.value = null
  if (!name || name === oldName) return
  try {
    await catalogsApi.rename(props.scope, oldName, name)
    if (props.modelValue === oldName) emit('update:modelValue', name)
    await reload()
    emit('changed')
    toast.success(`Каталог переименован в «${name}»`)
  } catch (e) { toast.error(e.message) }
}

async function remove(name) {
  menu.value.visible = false
  const n = counts.value[name] || 0
  const ok = await confirmDialog({
    title: 'Удалить каталог?',
    message: n ? `Каталог «${name}» содержит записей: ${n}.\nСами записи не удалятся — они станут «без каталога».` : `Каталог «${name}» пуст.`,
  })
  if (!ok) return
  try {
    await catalogsApi.delete(props.scope, name)
    if (props.modelValue === name) emit('update:modelValue', '')
    await reload()
    emit('changed')
    toast.success(`Каталог «${name}» удалён`)
  } catch (e) { toast.error(e.message) }
}

async function onDrop(target, e) {
  dragOver.value = null
  if (target === undefined) return // «Все записи» — не действие
  let ids = []
  try { ids = JSON.parse(e.dataTransfer.getData('application/x-atlas-ids') || '[]') } catch { /* чужой drag */ }
  if (!ids.length) return
  try {
    await catalogsApi.move(props.scope, ids, target)
    await reload()
    emit('changed')
    toast.success(target ? `Перемещено в «${target}»` : 'Убрано из каталога')
  } catch (err) { toast.error(err.message) }
}

function openMenu(name, e) {
  const x = Math.min(e.clientX, window.innerWidth - 210)
  const y = Math.min(e.clientY, window.innerHeight - 140)
  menu.value = { visible: true, x, y, name }
}
const closeMenu = () => { menu.value.visible = false }
onMounted(() => { reload(); document.addEventListener('click', closeMenu) })
onBeforeUnmount(() => document.removeEventListener('click', closeMenu))
</script>

<style scoped>
.catalog-sidebar {
  background: var(--c-bg2); border: 1px solid var(--c-border); border-radius: var(--radius);
  padding: 10px 8px; position: sticky; top: 0; max-height: calc(100vh - var(--header-h) - 60px); overflow-y: auto;
}
.catalog-sidebar__head { display: flex; align-items: center; justify-content: space-between; padding: 0 4px 8px; border-bottom: 1px solid var(--c-border); margin-bottom: 6px; }
.catalog-sidebar__title { font-size: 12px; font-weight: 600; color: var(--c-text2); text-transform: uppercase; letter-spacing: 0.04em; }
.catalog-new { padding: 6px 4px 10px; }
.catalog-list { border-top: 1px dashed var(--c-border); margin-top: 4px; padding-top: 4px; }
.catalog-item { display: flex; align-items: center; gap: 7px; padding: 7px 8px; border-radius: 7px; cursor: pointer; font-size: 13px; border: 1px solid transparent; margin-bottom: 2px; user-select: none; }
.catalog-item:hover { background: var(--c-bg3); }
.catalog-item.active { background: rgba(79,124,255,0.12); color: var(--c-accent); border-color: rgba(79,124,255,0.25); }
.catalog-item.drop-target { background: var(--c-surface); border-color: var(--c-accent); border-style: dashed; }
.catalog-item__icon { font-size: 14px; flex-shrink: 0; }
.catalog-item__name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.catalog-item__count { font-size: 11px; color: var(--c-text3); background: var(--c-bg3); padding: 1px 6px; border-radius: 10px; }
.catalog-item__more { background: none; border: none; color: var(--c-text3); cursor: pointer; padding: 0 2px; opacity: 0; }
.catalog-item:hover .catalog-item__more, .catalog-item:focus-within .catalog-item__more { opacity: 1; }
.catalog-rename { flex: 1; }
.catalog-hint { font-size: 11px; color: var(--c-text3); padding: 8px 6px 2px; line-height: 1.4; }
@media (hover: none) { .catalog-item__more { opacity: 1; } }
</style>
