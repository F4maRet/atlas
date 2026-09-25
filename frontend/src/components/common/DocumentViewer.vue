<template>
  <div class="viewer">
    <div v-if="!src" class="viewer-state">
      <div class="viewer-state__icon">📎</div>
      <div class="text-muted text-sm">{{ emptyText }}</div>
    </div>

    <div v-else-if="loading" class="viewer-state">
      <div class="spinner"></div>
      <div class="text-muted text-sm mt-3">Загрузка документа…</div>
    </div>

    <div v-else-if="error" class="viewer-state">
      <div class="viewer-state__icon">⚠️</div>
      <div style="font-weight:600;margin-bottom:6px">Не удалось загрузить предпросмотр</div>
      <div class="text-muted text-sm" style="margin-bottom:16px">{{ error }}</div>
      <a v-if="downloadUrl" :href="downloadUrl" class="btn btn-primary btn-sm" download>↓ Скачать файл</a>
    </div>

    <!-- PDF: сервер отдаёт inline, браузер показывает своим просмотрщиком -->
    <iframe v-else-if="kind === 'pdf'" :src="src" class="viewer-frame" title="PDF"></iframe>

    <div v-else-if="kind === 'image'" class="viewer-image">
      <img :src="src" :alt="filename" />
    </div>

    <pre v-else-if="text !== null" class="viewer-text">{{ text }}</pre>

    <!-- HTML (DOCX → HTML). Без allow-scripts: скрипты внутри не выполняются -->
    <iframe v-else-if="html" :srcdoc="html" class="viewer-frame viewer-frame--doc" sandbox title="Документ"></iframe>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import api from '@/utils/api'
import { fileExt } from '@/utils/format'

const props = defineProps({
  src: String, // URL /preview
  filename: String,
  downloadUrl: String,
  emptyText: { type: String, default: 'Выберите документ для просмотра' },
})

const loading = ref(false)
const error = ref('')
const html = ref('')
const text = ref(null)

const kind = computed(() => {
  const ext = fileExt(props.filename)
  if (ext === 'pdf') return 'pdf'
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) return 'image'
  return 'fetch'
})

let seq = 0
async function load() {
  html.value = ''
  text.value = null
  error.value = ''
  if (!props.src || kind.value !== 'fetch') return
  const my = ++seq
  loading.value = true
  try {
    const r = await api.get(props.src, { responseType: 'text', transformResponse: x => x, baseURL: '' })
    if (my !== seq) return
    const ctype = r.headers['content-type'] || ''
    if (ctype.startsWith('text/plain')) text.value = r.data
    else html.value = r.data
  } catch (e) {
    if (my === seq) error.value = e.message
  } finally {
    if (my === seq) loading.value = false
  }
}

watch(() => [props.src, props.filename], load, { immediate: true })
</script>

<style scoped>
.viewer { position: relative; flex: 1; min-width: 0; min-height: 320px; display: flex; background: #e9eaee; }
.viewer-frame { flex: 1; width: 100%; height: 100%; border: none; background: #fff; }
.viewer-state {
  position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: var(--c-bg2); color: var(--c-text); padding: 32px; text-align: center;
}
.viewer-state__icon { font-size: 40px; margin-bottom: 10px; opacity: 0.8; }
.viewer-image { flex: 1; display: flex; align-items: center; justify-content: center; overflow: auto; padding: 16px; }
.viewer-image img { max-width: 100%; max-height: 100%; object-fit: contain; box-shadow: var(--shadow); }
.viewer-text {
  flex: 1; margin: 0; padding: 16px 20px; overflow: auto; background: var(--c-bg); color: var(--c-text);
  font-family: var(--font-mono); font-size: 12px; white-space: pre-wrap; word-break: break-word;
}
</style>
