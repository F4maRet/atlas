<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modelValue" class="modal-overlay" @mousedown.self="onOverlay">
        <div
          ref="dialog"
          class="modal"
          :class="[`modal--${size}`, { 'modal--flush': flush }]"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
          tabindex="-1"
        >
          <div v-if="title || $slots.header" class="modal-header">
            <slot name="header">
              <h2 class="modal-title">{{ title }}</h2>
            </slot>
            <button class="btn btn-ghost btn-sm btn-icon" title="Закрыть (Esc)" aria-label="Закрыть" @click="close">✕</button>
          </div>
          <div class="modal-body">
            <slot />
          </div>
          <div v-if="$slots.footer" class="modal-footer">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
// Стек открытых окон: Esc закрывает только верхнее
const stack = []
</script>

<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  title: String,
  size: { type: String, default: 'md' }, // sm | md | lg | xl
  flush: Boolean, // без внутренних отступов (для раскладок с панелями)
  persistent: Boolean, // не закрывать кликом по фону
})
const emit = defineEmits(['update:modelValue', 'close'])
const dialog = ref(null)
const token = Symbol('modal')

function close() {
  emit('update:modelValue', false)
  emit('close')
}
function onOverlay() {
  if (!props.persistent) close()
}
function onKey(e) {
  if (e.key === 'Escape' && stack[stack.length - 1] === token) {
    e.stopPropagation()
    close()
  }
}

function open() {
  stack.push(token)
  document.addEventListener('keydown', onKey)
  document.body.classList.add('no-scroll')
  nextTick(() => {
    const el = dialog.value?.querySelector('[autofocus], input:not([type=hidden]), textarea, select')
    ;(el || dialog.value)?.focus?.()
  })
}
function release() {
  const i = stack.indexOf(token)
  if (i !== -1) stack.splice(i, 1)
  document.removeEventListener('keydown', onKey)
  if (!stack.length) document.body.classList.remove('no-scroll')
}

watch(() => props.modelValue, v => (v ? open() : release()), { immediate: true })
onBeforeUnmount(release)
</script>
