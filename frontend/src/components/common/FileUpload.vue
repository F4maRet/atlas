<template>
  <div>
    <div
      class="dropzone"
      :class="{ active: dragDepth > 0, 'dropzone--filled': !!modelValue }"
      role="button"
      tabindex="0"
      @click="pick"
      @keydown.enter.prevent="pick"
      @keydown.space.prevent="pick"
      @dragenter.prevent="dragDepth++"
      @dragover.prevent
      @dragleave="dragDepth = Math.max(0, dragDepth - 1)"
      @drop.prevent="onDrop"
    >
      <div v-if="!modelValue">
        <div class="dropzone__icon">{{ icon }}</div>
        <div class="dropzone__text">
          <strong>Нажмите</strong> или перетащите файл<br>
          <span class="text-sm text-muted">{{ hint || accept }} · до {{ maxMb }} МБ</span>
        </div>
      </div>
      <div v-else class="file-info">
        <span>{{ fileIcon(modelValue.name) }}</span>
        <span class="file-info__name">{{ modelValue.name }}</span>
        <span class="file-info__size">{{ formatBytes(modelValue.size) }}</span>
        <button type="button" class="btn btn-ghost btn-sm btn-icon" title="Убрать" @click.stop="clear">✕</button>
      </div>
    </div>
    <input ref="input" type="file" :accept="accept" hidden @change="onSelect" />
    <div v-if="error" class="upload-error">{{ error }}</div>

    <!-- Уже загруженный файл -->
    <div v-if="existingName && !modelValue" class="file-info mt-2">
      <span>{{ fileIcon(existingName) }}</span>
      <span class="file-info__name">Текущий: {{ existingName }}</span>
      <span v-if="existingSizeOriginal" class="file-info__size">
        {{ formatBytes(existingSizeOriginal) }}
        <span v-if="ratio" class="compress-badge">▼ {{ ratio }}</span>
      </span>
      <a v-if="downloadUrl" :href="downloadUrl" class="btn btn-ghost btn-sm" download @click.stop>↓</a>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { formatBytes, compressionRatio, fileIcon, fileExt } from '@/utils/format'

const props = defineProps({
  modelValue: File,
  accept: { type: String, default: '' },
  hint: String,
  icon: { type: String, default: '📁' },
  maxMb: { type: Number, default: 100 },
  existingName: String,
  existingSizeOriginal: Number,
  existingSizeCompressed: Number,
  downloadUrl: String,
})
const emit = defineEmits(['update:modelValue'])

const input = ref(null)
const dragDepth = ref(0)
const error = ref('')

const ratio = computed(() => compressionRatio(props.existingSizeOriginal, props.existingSizeCompressed))

function pick() { input.value?.click() }

function accepts(file) {
  if (!props.accept) return true
  const ext = '.' + fileExt(file.name)
  return props.accept.split(',').map(s => s.trim().toLowerCase()).some(a =>
    a === ext || (a.endsWith('/*') && file.type.startsWith(a.slice(0, -1))) || a === file.type)
}

function take(file) {
  error.value = ''
  if (!file) return
  if (!accepts(file)) { error.value = `Неподдерживаемый формат. Допустимо: ${props.hint || props.accept}`; return }
  if (file.size > props.maxMb * 1024 * 1024) { error.value = `Файл больше ${props.maxMb} МБ`; return }
  emit('update:modelValue', file)
}
function onSelect(e) {
  take(e.target.files[0])
  e.target.value = '' // чтобы повторный выбор того же файла снова срабатывал
}
function onDrop(e) {
  dragDepth.value = 0
  take(e.dataTransfer.files[0])
}
function clear() { error.value = ''; emit('update:modelValue', null) }
</script>

<style scoped>
.dropzone--filled { padding: 10px; }
.upload-error { color: var(--c-red); font-size: 12px; margin-top: 6px; }
</style>
