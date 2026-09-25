import { reactive } from 'vue'

/** Глобальный диалог подтверждения (см. ConfirmDialog.vue в App.vue). */
export const confirmState = reactive({
  open: false,
  title: '',
  message: '',
  confirmText: 'Удалить',
  danger: true,
  resolve: null,
})

export function confirmDialog({ title = 'Подтверждение', message = '', confirmText = 'Удалить', danger = true } = {}) {
  if (confirmState.resolve) confirmState.resolve(false)
  Object.assign(confirmState, { open: true, title, message, confirmText, danger })
  return new Promise(resolve => { confirmState.resolve = resolve })
}

export function settleConfirm(value) {
  const r = confirmState.resolve
  confirmState.open = false
  confirmState.resolve = null
  r?.(value)
}
