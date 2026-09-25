<template>
  <Modal :model-value="confirmState.open" :title="confirmState.title" size="sm" @close="settleConfirm(false)">
    <p class="confirm-message">{{ confirmState.message }}</p>
    <template #footer>
      <button class="btn btn-secondary" @click="settleConfirm(false)">Отмена</button>
      <button
        ref="ok"
        class="btn"
        :class="confirmState.danger ? 'btn-danger-solid' : 'btn-primary'"
        @click="settleConfirm(true)"
      >{{ confirmState.confirmText }}</button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import Modal from './Modal.vue'
import { confirmState, settleConfirm } from '@/composables/useConfirm'

const ok = ref(null)
watch(() => confirmState.open, v => { if (v) nextTick(() => ok.value?.focus()) })
</script>

<style scoped>
.confirm-message { white-space: pre-line; color: var(--c-text2); line-height: 1.6; }
</style>
