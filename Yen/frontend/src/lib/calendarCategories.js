import { Stethoscope, TestTube, Pill, Syringe, Info } from '../components/icons.jsx'

export const CATEGORIES = [
  { value: 'kham_benh', label: 'Khám bệnh', icon: Stethoscope, dot: 'var(--cal-blue)' },
  { value: 'xet_nghiem', label: 'Xét nghiệm', icon: TestTube, dot: 'var(--cal-purple)' },
  { value: 'thuoc', label: 'Thuốc / Nhắc nhở', icon: Pill, dot: 'var(--amber-warm)' },
  { value: 'tiem_chung', label: 'Tiêm chủng', icon: Syringe, dot: 'var(--green)' },
  { value: 'khac', label: 'Khác', icon: Info, dot: 'var(--ink-faint)' },
]

const CATEGORY_MAP = Object.fromEntries(CATEGORIES.map((c) => [c.value, c]))

export function categoryMeta(value) {
  return CATEGORY_MAP[value] || CATEGORIES[CATEGORIES.length - 1]
}
