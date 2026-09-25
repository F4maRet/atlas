<template>
  <Modal :model-value="modelValue" size="xl" flush @update:model-value="$emit('update:modelValue', $event)">
    <template #header>
      <div class="pv-head">
        <span class="pv-icon">{{ fileIcon(filename) }}</span>
        <div class="pv-meta">
          <div class="pv-name" :title="filename">{{ title || filename }}</div>
          <div v-if="title" class="text-muted text-sm truncate">{{ filename }}</div>
        </div>
        <a v-if="downloadUrl" :href="downloadUrl" class="btn btn-ghost btn-sm" download>↓ Скачать</a>
      </div>
    </template>
    <div class="pv-body">
      <DocumentViewer v-if="modelValue" :src="previewUrl" :filename="filename" :download-url="downloadUrl" />
    </div>
  </Modal>
</template>

<script setup>
import Modal from './Modal.vue'
import DocumentViewer from './DocumentViewer.vue'
import { fileIcon } from '@/utils/format'

defineProps({
  modelValue: Boolean,
  previewUrl: String,
  downloadUrl: String,
  filename: String,
  title: String,
})
defineEmits(['update:modelValue'])
</script>

<style scoped>
.pv-head { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; margin-right: 8px; }
.pv-icon { font-size: 22px; }
.pv-meta { min-width: 0; flex: 1; }
.pv-name { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pv-body { height: calc(90vh - 70px); display: flex; }
</style>
