<template>
  <div class="file-tree">
    <TreeNode v-for="node in nodes" :key="node.path" :node="node" :depth="0" @select="$emit('select', $event)" />
  </div>
</template>

<script setup>
import TreeNode from './TreeNode.vue'
defineProps({ nodes: Array })
defineEmits(['select'])
</script>
