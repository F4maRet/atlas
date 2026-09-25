import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'

export function formatBytes(bytes) {
  if (!bytes) return '0 Б'
  const units = ['Б', 'КБ', 'МБ', 'ГБ']
  let i = 0
  while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++ }
  return `${i === 0 ? bytes : bytes.toFixed(1)} ${units[i]}`
}

/** «-42%» — экономия места при сжатии (или null, если несущественна) */
export function compressionRatio(original, compressed) {
  if (!original || !compressed) return null
  const saved = Math.round((1 - compressed / original) * 100)
  return saved > 2 ? `-${saved}%` : null
}

function toDate(d) {
  if (!d) return null
  return d instanceof Date ? d : parseISO(d)
}

export const formatDate = (d, pattern = 'd MMM yyyy') => (d ? format(toDate(d), pattern, { locale: ru }) : '')
export const formatDateShort = d => formatDate(d, 'd MMM')
export const formatDateNum = d => formatDate(d, 'dd.MM.yyyy')

export function formatRange(start, end) {
  if (!start && !end) return ''
  if (!end || start === end) return formatDate(start)
  if (!start) return `по ${formatDate(end)}`
  return `${formatDate(start)} — ${formatDate(end)}`
}

/** 'Лаукарт Михаил Сергеевич' → 'Лаукарт М.С.' */
export function abbreviateName(fullName) {
  if (!fullName) return ''
  const [surname, ...rest] = fullName.trim().split(/\s+/)
  const initials = rest.flatMap(p => p.split('.')).filter(Boolean).map(p => p[0].toUpperCase() + '.').join('')
  return initials ? `${surname} ${initials}` : surname
}

/** pluralize(5, 'статья', 'статьи', 'статей') → '5 статей' */
export function pluralize(n, one, few, many) {
  const m10 = n % 10, m100 = n % 100
  const word = m100 >= 11 && m100 <= 14 ? many : m10 === 1 ? one : m10 >= 2 && m10 <= 4 ? few : many
  return `${n} ${word}`
}

export const fileExt = name => (name && name.includes('.') ? name.split('.').pop().toLowerCase() : '')

export function fileIcon(name) {
  const ext = fileExt(name)
  if (ext === 'pdf') return '📕'
  if (['doc', 'docx', 'odt', 'rtf'].includes(ext)) return '📘'
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) return '🖼'
  if (ext === 'zip') return '🗜'
  return '📄'
}

// Локальная дата (toISOString давал UTC — после полуночи по Москве «сегодня» было вчера)
export const today = () => format(new Date(), 'yyyy-MM-dd')

export function authorLabel(a) {
  return a?.short_name || abbreviateName(a?.full_name) || ''
}
