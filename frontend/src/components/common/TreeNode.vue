<template>
  <div class="tree-node" :style="{ paddingLeft: depth * 14 + 'px' }">
    <div
      class="tree-node__row"
      :class="{ 'tree-node__row--dir': node.type === 'dir', 'tree-node__row--file': node.type === 'file' }"
      @click="toggle"
    >
      <span class="tree-node__icon">
        {{ node.type === 'dir' ? (open ? '📂' : '📁') : fileIcon(node.name) }}
      </span>
      <span class="tree-node__name">{{ node.name }}</span>
    </div>
    <div v-if="node.type === 'dir' && open && node.children">
      <TreeNode
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :depth="depth + 1"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const props = defineProps({ node: Object, depth: Number })
const emit = defineEmits(['select'])
const open = ref(false)

function toggle() {
  if (props.node.type === 'dir') {
    open.value = !open.value
  } else {
    emit('select', props.node.path)
  }
}

function fileIcon(name) {
  const ext = name.split('.').pop()?.toLowerCase()
  const map = { py: '🐍', js: '📜', ts: '📜', vue: '💚', html: '🌐', css: '🎨', json: '📋', md: '📝', txt: '📄', sql: '🗃', sh: '⚙️', dockerfile: '🐳', yml: '⚙️', yaml: '⚙️', xml: '📋', csv: '📊', png: '🖼', jpg: '🖼', pdf: '📕', zip: '🗜', gz: '🗜' }
  return map[ext] || '📄'
}
</script>

<style scoped>
.tree-node__row {
  display: flex; align-items: center; gap: 6px;
  padding: 3px 6px; border-radius: 4px; cursor: pointer;
  font-size: 12px; color: var(--c-text2);
  transition: background 0.1s;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.tree-node__row--file:hover { background: var(--c-surface); color: var(--c-accent); }
.tree-node__row--dir { color: var(--c-text); font-weight: 500; }
.tree-node__row--dir:hover { background: var(--c-surface); }
.tree-node__icon { font-size: 13px; flex-shrink: 0; }
.tree-node__name { overflow: hidden; text-overflow: ellipsis; }
</style>
