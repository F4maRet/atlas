<template>
  <Transition name="fade">
    <div v-if="modelValue" class="preview-overlay" @click.self="close">
      <div class="preview-window">
        <!-- Header -->
        <div class="preview-header">
          <div class="preview-header__left">
            <span class="preview-icon">{{ fileIcon }}</span>
            <div>
              <div class="preview-filename">{{ filename }}</div>
              <div class="preview-type text-muted text-sm">{{ typeLabel }}</div>
            </div>
          </div>
          <div class="preview-header__actions">
            <a :href="downloadUrl" class="btn btn-ghost btn-sm" download :download="filename" title="Скачать">↓ Скачать</a>
            <button class="btn btn-ghost btn-sm btn-icon" @click="close" title="Закрыть">✕</button>
          </div>
        </div>

        <!-- Body -->
        <div class="preview-body">
          <!-- Loading -->
          <div v-if="loading" class="preview-state">
            <div class="preview-spinner"></div>
            <div class="text-muted text-sm" style="margin-top:12px">Загрузка документа...</div>
          </div>

          <!-- Error -->
          <div v-else-if="error" class="preview-state">
            <div style="font-size:40px;margin-bottom:12px">⚠️</div>
            <div style="font-weight:600;margin-bottom:6px">Не удалось загрузить</div>
            <div class="text-muted text-sm" style="margin-bottom:16px">{{ error }}</div>
            <a :href="downloadUrl" class="btn btn-primary" :download="filename">↓ Скачать файл</a>
          </div>

          <!-- PDF via object (native, no external service) -->
          <object
            v-else-if="isPdf && !loading && !error"
            :data="previewUrl"
            type="application/pdf"
            class="preview-iframe"
          >
            <div class="preview-state">
              <div style="font-size:40px;margin-bottom:12px">📕</div>
              <div style="font-weight:600;margin-bottom:6px">Браузер не поддерживает встроенный PDF-просмотр</div>
              <a :href="downloadUrl" class="btn btn-primary" :download="filename">↓ Скачать PDF</a>
            </div>
          </object>

          <!-- DOCX rendered as HTML locally via /preview endpoint -->
          <iframe
            v-else-if="(isDocx || isDoc) && htmlContent && !loading && !error"
            :srcdoc="htmlContent"
            class="preview-iframe"
            title="Document preview"
            sandbox="allow-same-origin"
          ></iframe>

          <!-- Unsupported format -->
          <div v-else-if="!loading && !error" class="preview-state">
            <div style="font-size:40px;margin-bottom:12px">📎</div>
            <div style="font-weight:600;margin-bottom:6px">Предпросмотр недоступен</div>
            <div class="text-muted text-sm" style="margin-bottom:16px">Формат .{{ fileExt }} не поддерживается для просмотра</div>
            <a :href="downloadUrl" class="btn btn-primary" :download="filename">↓ Скачать файл</a>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  previewUrl: String,
  downloadUrl: String,
  filename: String,
})

const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const error = ref('')
const htmlContent = ref('')

const fileExt = computed(() => {
  if (!props.filename) return ''
  return props.filename.split('.').pop().toLowerCase()
})

const isPdf  = computed(() => fileExt.value === 'pdf')
const isDocx = computed(() => fileExt.value === 'docx')
const isDoc  = computed(() => fileExt.value === 'doc')

const fileIcon = computed(() => {
  if (isPdf.value)          return '📕'
  if (isDocx.value || isDoc.value) return '📘'
  return '📄'
})

const typeLabel = computed(() => {
  if (isPdf.value)  return 'PDF документ'
  if (isDocx.value) return 'Word документ (DOCX)'
  if (isDoc.value)  return 'Word документ (DOC)'
  return `Файл .${fileExt.value}`
})

function close() {
  emit('update:modelValue', false)
}

watch(() => props.modelValue, async (visible) => {
  if (!visible) {
    htmlContent.value = ''
    error.value = ''
    loading.value = false
    return
  }
  if (!props.previewUrl) return

  if (isPdf.value) {
    // PDF served locally via /preview endpoint (or direct download URL)
    loading.value = false
    return
  }

  if (isDocx.value || isDoc.value) {
    // DOCX/DOC: fetch HTML rendered server-side via python-docx (no Google, no internet)
    loading.value = true
    error.value = ''
    try {
      const resp = await fetch(props.previewUrl)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      htmlContent.value = await resp.text()
    } catch (e) {
      error.value = `Ошибка загрузки: ${e.message}`
    } finally {
      loading.value = false
    }
    return
  }

  loading.value = false
})
</script>

<style scoped>
.preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: rgba(0,0,0,0.78);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(4px);
}

.preview-window {
  background: var(--c-bg2);
  border: 1px solid var(--c-border2);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 1050px;
  height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 32px 96px rgba(0,0,0,0.7);
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-bottom: 1px solid var(--c-border);
  background: var(--c-bg3);
  flex-shrink: 0;
  gap: 12px;
}

.preview-header__left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.preview-icon { font-size: 22px; flex-shrink: 0; }

.preview-filename {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 550px;
}

.preview-type { font-size: 11px; }

.preview-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.preview-body {
  flex: 1;
  overflow: hidden;
  position: relative;
  background: #f0f0f0;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
  background: #fff;
}

.preview-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--c-bg2);
  color: var(--c-text);
  padding: 40px;
  text-align: center;
}

.preview-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--c-border2);
  border-top-color: var(--c-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
