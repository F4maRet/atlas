<template>
  <div>
    <div
      class="dropzone"
      :class="{ active: isDragging }"
      @click="$refs.input.click()"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="onDrop"
    >
      <div v-if="!modelValue">
        <div class="dropzone__icon">{{ icon }}</div>
        <div class="dropzone__text">
          <strong>Нажмите</strong> или перетащите файл<br>
          <span class="text-sm text-muted">{{ accept }} · макс {{ maxMb }} МБ</span>
        </div>
      </div>
      <div v-else class="file-info">
        <span>📎</span>
        <span class="file-info__name">{{ modelValue.name }}</span>
        <span class="file-info__size">{{ formatBytes(modelValue.size) }}</span>
        <button class="btn btn-ghost btn-sm btn-icon" @click.stop="clear">✕</button>
      </div>
    </div>
    <input ref="input" type="file" :accept="accept" style="display:none" @change="onSelect" />

    <!-- Existing file info -->
    <div v-if="existingName && !modelValue" class="file-info mt-2">
      <span>📎</span>
      <span class="file-info__name">{{ existingName }}</span>
      <span v-if="existingSizeOriginal" class="file-info__size">
        {{ formatBytes(existingSizeOriginal) }}
        <span v-if="compressionRatio" class="compress-badge">▼ {{ compressionRatio }}</span>
      </span>
      <a :href="downloadUrl" target="_blank" class="btn btn-ghost btn-sm" @click.stop>↓ Скачать</a>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { formatBytes } from '@/utils/api'

const props = defineProps({
  modelValue: File,
  accept: { type: String, default: '*' },
  icon: { type: String, default: '📁' },
  maxMb: { type: Number, default: 100 },
  existingName: String,
  existingSizeOriginal: Number,
  existingSizeCompressed: Number,
  downloadUrl: String,
})
const emit = defineEmits(['update:modelValue'])

const isDragging = ref(false)

const compressionRatio = computed(() => {
  if (!props.existingSizeOriginal || !props.existingSizeCompressed) return null
  const saved = ((1 - props.existingSizeCompressed / props.existingSizeOriginal) * 100).toFixed(0)
  return saved > 2 ? `-${saved}%` : null
})

function onSelect(e) {
  const file = e.target.files[0]
  if (file) emit('update:modelValue', file)
}
function onDrop(e) {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) emit('update:modelValue', file)
}
function clear() {
  emit('update:modelValue', null)
}
</script>
