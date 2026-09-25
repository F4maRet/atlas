<template>
  <div class="file-tree">
    <div v-if="!nodes?.length" class="text-muted text-sm" style="padding:8px">Архив пуст</div>
    <TreeNode
      v-for="node in nodes"
      :key="node.path"
      :node="node"
      :depth="0"
      :selected="selected"
      :expanded="expanded"
      @select="$emit('select', $event)"
    />
  </div>
</template>

<script setup>
import TreeNode from './TreeNode.vue'
defineProps({ nodes: Array, selected: String, expanded: Boolean })
defineEmits(['select'])
</script>
