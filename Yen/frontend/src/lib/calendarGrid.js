export function pad(n) {
  return String(n).padStart(2, '0')
}

export function toISODate(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function monthKey(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`
}

/** Cộng n ngày vào 1 chuỗi ISO 'YYYY-MM-DD', trả về chuỗi ISO. */
export function addDays(iso, n) {
  const d = new Date(iso + 'T00:00:00')
  d.setDate(d.getDate() + n)
  return toISODate(d)
}

/** Lưới đủ 6 hàng x 7 cột, có kèm ngày đầu/cuối tháng liền kề (đánh dấu inMonth: false). */
export function buildMonthGrid(year, month) {
  const first = new Date(year, month, 1)
  const startOffset = (first.getDay() + 6) % 7 // 0 = Thứ 2
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells = []
  for (let i = startOffset; i > 0; i--) {
    cells.push({ date: new Date(year, month, 1 - i), inMonth: false })
  }
  for (let day = 1; day <= daysInMonth; day++) {
    cells.push({ date: new Date(year, month, day), inMonth: true })
  }
  while (cells.length % 7 !== 0 || cells.length < 42) {
    const last = cells[cells.length - 1].date
    cells.push({ date: new Date(last.getFullYear(), last.getMonth(), last.getDate() + 1), inMonth: false })
  }
  return cells
}
