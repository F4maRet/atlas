<template>
  <div class="tree-node">
    <div
      class="tree-node__row"
      :class="{ 'tree-node__row--dir': node.type === 'dir', 'tree-node__row--active': node.path === selected }"
      :style="{ paddingLeft: 6 + depth * 14 + 'px' }"
      :title="node.path"
      @click="toggle"
    >
      <span class="tree-node__icon">{{ node.type === 'dir' ? (open ? '📂' : '📁') : fileIcon(node.name) }}</span>
      <span class="tree-node__name">{{ node.name }}</span>
      <span v-if="node.type === 'file' && node.size != null" class="tree-node__size">{{ formatBytes(node.size) }}</span>
    </div>
    <div v-if="node.type === 'dir' && open">
      <TreeNode
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :depth="depth + 1"
        :selected="selected"
        :expanded="expanded"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { formatBytes } from '@/utils/format'

const props = defineProps({ node: Object, depth: Number, selected: String, expanded: Boolean })
const emit = defineEmits(['select'])
// Верхний уровень раскрыт сразу — раньше приходилось щёлкать по каждой папке
const open = ref(props.depth === 0 || props.expanded)
watch(() => props.expanded, v => { open.value = v || props.depth === 0 })

function toggle() {
  if (props.node.type === 'dir') open.value = !open.value
  else emit('select', props.node)
}

const ICONS = {
  py: '🐍', js: '📜', ts: '📜', vue: '💚', html: '🌐', css: '🎨', json: '📋', md: '📝', txt: '📄', sql: '🗃',
  sh: '⚙️', bat: '⚙️', yml: '⚙️', yaml: '⚙️', xml: '📋', csv: '📊', png: '🖼', jpg: '🖼', jpeg: '🖼', gif: '🖼',
  pdf: '📕', doc: '📘', docx: '📘', zip: '🗜', gz: '🗜', exe: '⚙️', dll: '⚙️', c: '🔧', cpp: '🔧', h: '🔧',
  cs: '🔧', java: '☕', go: '🔧', rs: '🔧', php: '🐘',
}
function fileIcon(name) {
  const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : name.toLowerCase()
  return ICONS[ext] || '📄'
}
</script>

<style scoped>
.tree-node__row {
  display: flex; align-items: center; gap: 6px;
  padding: 3px 6px; border-radius: 4px; cursor: pointer;
  font-size: 12px; color: var(--c-text2); white-space: nowrap;
}
.tree-node__row:hover { background: var(--c-surface); color: var(--c-text); }
.tree-node__row--dir { color: var(--c-text); font-weight: 500; }
.tree-node__row--active { background: rgba(79,124,255,0.15); color: var(--c-accent); }
.tree-node__icon { font-size: 13px; flex-shrink: 0; }
.tree-node__name { overflow: hidden; text-overflow: ellipsis; flex: 1; min-width: 0; }
.tree-node__size { font-size: 10px; color: var(--c-text3); flex-shrink: 0; }
</style>
