<template>
  <th class="sort-th" :class="{ active: sortKey === k }" :aria-sort="ariaSort" tabindex="0"
    @click="toggle(k)" @keydown.enter="toggle(k)">
    <slot />
    <span class="sort-th__arrow">{{ sortKey === k ? (sortDir === 'asc' ? '▲' : '▼') : '↕' }}</span>
  </th>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ k: String, sortKey: String, sortDir: String, toggle: Function })
const ariaSort = computed(() => (props.sortKey === props.k ? (props.sortDir === 'asc' ? 'ascending' : 'descending') : 'none'))
</script>

<style scoped>
.sort-th { cursor: pointer; user-select: none; white-space: nowrap; }
.sort-th:hover { color: var(--c-text); }
.sort-th.active { color: var(--c-accent); }
.sort-th__arrow { font-size: 9px; margin-left: 4px; opacity: 0.5; }
.sort-th.active .sort-th__arrow { opacity: 1; }
</style>
