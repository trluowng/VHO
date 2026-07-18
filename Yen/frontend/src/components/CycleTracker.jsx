import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { cycleApi } from '../lib/api.js'
import { toISODate, buildMonthGrid } from '../lib/calendarGrid.js'
import { Calendar as CalendarIcon, Droplet, Heart, Info, Sparkle, X } from './icons.jsx'

const WEEKDAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

const PHASE_META = {
  period: {
    label: 'Đang hành kinh',
    color: '#e85f76',
    description: 'Ngày hành kinh đã được ghi nhận trong chu kỳ của bạn.',
  },
  'period-predicted': {
    label: 'Dự đoán hành kinh',
    color: '#e85f76',
    description: 'Ngày bắt đầu kỳ kinh tiếp theo được ước tính từ lịch sử đã ghi nhận.',
  },
  fertile: {
    label: 'Ngày dễ mang thai',
    color: '#8c75dc',
    description: 'Khả năng mang thai có thể cao hơn trong khoảng thời gian này.',
  },
  ovulation: {
    label: 'Rụng trứng ước tính',
    color: '#7258c8',
    description: 'Đây là ngày rụng trứng được ước tính từ độ dài chu kỳ đã ghi nhận.',
  },
  safe: {
    label: 'Ngày an toàn (ước lượng)',
    color: '#2aa98b',
    description: 'Khả năng mang thai được ước tính thấp hơn, nhưng đây không phải biện pháp tránh thai.',
  },
}

function formatVi(dateStr) {
  if (!dateStr) return '—'
  const date = new Date(`${dateStr}T00:00:00`)
  return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function formatShortRange(start, end) {
  if (!start || !end) return '—'
  return `${formatVi(start)} – ${formatVi(end)}`
}

function addDaysIso(iso, days) {
  const date = new Date(`${iso}T00:00:00`)
  date.setDate(date.getDate() + days)
  return toISODate(date)
}

function daysBetweenIso(first, second) {
  return Math.round((new Date(`${second}T00:00:00`) - new Date(`${first}T00:00:00`)) / 86400000)
}

function inRange(iso, start, end) {
  return start && end && iso >= start && iso <= end
}

/** Ngày kinh (đã ghi nhận hoặc dự đoán) > ngày dễ mang thai > ngày an toàn ước lượng. */
function classifyDay(iso, entries, prediction) {
  const periodLength = prediction?.period_length_days || 5
  for (const entry of entries) {
    if (inRange(iso, entry.period_start_date, addDaysIso(entry.period_start_date, periodLength - 1))) return 'period'
  }
  if (inRange(iso, prediction?.predicted_period_start, prediction?.predicted_period_end)) return 'period-predicted'
  if (iso === prediction?.ovulation_date) return 'ovulation'
  if (inRange(iso, prediction?.fertile_window_start, prediction?.fertile_window_end)) return 'fertile'
  return 'safe'
}

function CycleProgressBar({ prediction }) {
  const cycleLength = prediction?.average_cycle_length_days || 28
  const periodLength = prediction?.period_length_days || 5
  const todayDay = prediction?.current_cycle_day || 1
  const fertileStartDay = prediction?.last_period_start_date && prediction?.fertile_window_start
    ? daysBetweenIso(prediction.last_period_start_date, prediction.fertile_window_start) + 1
    : null
  const fertileEndDay = prediction?.last_period_start_date && prediction?.fertile_window_end
    ? daysBetweenIso(prediction.last_period_start_date, prediction.fertile_window_end) + 1
    : null
  const ovulationDay = prediction?.last_period_start_date && prediction?.ovulation_date
    ? daysBetweenIso(prediction.last_period_start_date, prediction.ovulation_date) + 1
    : null
  const total = Math.max(cycleLength, todayDay, fertileEndDay || 0)
  const boundedTodayDay = Math.min(total, Math.max(1, todayDay))
  const todayPosition = `${((boundedTodayDay - 0.5) / total) * 100}%`
  const todayAlignment = boundedTodayDay <= 4 ? 'start' : boundedTodayDay >= total - 3 ? 'end' : 'center'
  const timeline = Array.from({ length: total }, (_, index) => {
    const day = index + 1
    let kind = 'safe'
    if (day <= periodLength) kind = 'period'
    else if (day === ovulationDay) kind = 'ovulation'
    else if (fertileStartDay && fertileEndDay && day >= fertileStartDay && day <= fertileEndDay) kind = 'fertile'
    return { day, kind }
  })

  return (
    <div className="cycle-progress">
      <div className="cycle-progress__track" aria-label={`Tiến trình chu kỳ ${total} ngày, hôm nay là ngày ${todayDay}`}>
        <span className={`cycle-progress__today-label is-${todayAlignment}`} style={{ left: todayPosition }}>Hôm nay · ngày {todayDay}</span>
        <div className="cycle-progress__days" style={{ '--cycle-days': total }}>
          {timeline.map(({ day, kind }) => (
            <span key={day} className={`cycle-progress__day cycle-progress__day--${kind}`} title={`Ngày ${day}: ${PHASE_META[kind].label}`} />
          ))}
        </div>
        <div className="cycle-progress__marker" style={{ left: todayPosition }} title={`Hôm nay: ngày ${todayDay}`} />
      </div>
      <div className="cycle-progress__labels">
        <span>Ngày 1</span>
        <span>Ngày {total}</span>
      </div>
    </div>
  )
}

export default function CycleTracker() {
  const { token } = useAuth()
  const [entries, setEntries] = useState([])
  const [prediction, setPrediction] = useState(null)
  const [cursor, setCursor] = useState(() => new Date())
  const [selectedDate, setSelectedDate] = useState(() => toISODate(new Date()))
  const [newDate, setNewDate] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [loaded, setLoaded] = useState(false)

  async function load() {
    try {
      const data = await cycleApi.list(token)
      setEntries(data.entries)
      setPrediction(data.prediction)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoaded(true)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function addEntry(event) {
    event.preventDefault()
    if (!newDate) return
    setBusy(true)
    setError(null)
    try {
      const data = await cycleApi.create(token, { period_start_date: newDate, note: note || null })
      setEntries(data.entries)
      setPrediction(data.prediction)
      const recordedDate = new Date(`${newDate}T00:00:00`)
      setCursor(new Date(recordedDate.getFullYear(), recordedDate.getMonth(), 1))
      setSelectedDate(newDate)
      setNewDate('')
      setNote('')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function removeEntry(id) {
    setBusy(true)
    setError(null)
    try {
      const data = await cycleApi.remove(token, id)
      setEntries(data.entries)
      setPrediction(data.prediction)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const grid = useMemo(() => buildMonthGrid(cursor.getFullYear(), cursor.getMonth()), [cursor])
  const todayIso = toISODate(new Date())
  const hasData = entries.length > 0
  const todayPhase = hasData ? classifyDay(todayIso, entries, prediction) : null
  const phaseMeta = todayPhase ? PHASE_META[todayPhase] : null
  const cycleLength = prediction?.average_cycle_length_days || 28
  const cycleDay = prediction?.current_cycle_day || 1
  const cyclePercentage = hasData
    ? `${Math.min(100, Math.max(0, (cycleDay / Math.max(cycleLength, cycleDay)) * 100))}%`
    : '0%'
  const daysUntilNextPeriod = prediction?.predicted_period_start
    ? daysBetweenIso(todayIso, prediction.predicted_period_start)
    : null
  const selectedKind = hasData ? classifyDay(selectedDate, entries, prediction) : null
  const selectedMeta = selectedKind ? PHASE_META[selectedKind] : null
  const selectedIsToday = selectedDate === todayIso
  const selectedIsOvulation = selectedDate === prediction?.ovulation_date
  const selectedCycleDay = prediction?.last_period_start_date
    ? daysBetweenIso(prediction.last_period_start_date, selectedDate) + 1
    : null
  const selectedEntry = entries.find((entry) => inRange(
    selectedDate,
    entry.period_start_date,
    addDaysIso(entry.period_start_date, (prediction?.period_length_days || 5) - 1),
  ))
  const SelectedDayIcon = selectedKind === 'period' || selectedKind === 'period-predicted'
    ? Droplet
    : selectedKind === 'fertile' || selectedKind === 'ovulation'
      ? Sparkle
      : CalendarIcon

  function moveMonth(offset) {
    const nextMonth = new Date(cursor.getFullYear(), cursor.getMonth() + offset, 1)
    setCursor(nextMonth)
    setSelectedDate(toISODate(nextMonth))
  }

  function selectDay(date, inMonth) {
    setSelectedDate(toISODate(date))
    if (!inMonth) setCursor(new Date(date.getFullYear(), date.getMonth(), 1))
  }

  function jumpToToday() {
    const today = new Date()
    setCursor(today)
    setSelectedDate(todayIso)
  }

  if (!loaded) {
    return <div className="cycle-loading"><span /> Đang tải dữ liệu chu kỳ…</div>
  }

  return (
    <div className="cycle-tracker">
      <section className={`cycle-hero ${hasData ? '' : 'is-empty'}`}>
        <div className="cycle-hero__main">
          <span className="cycle-hero__eyebrow"><Heart width={14} height={14} /> Theo dõi sức khỏe nữ</span>
          <h1>{hasData ? (phaseMeta?.label || 'Chu kỳ của bạn') : 'Hiểu chu kỳ của bạn mỗi ngày'}</h1>
          <p>
            {hasData
              ? 'Theo dõi kỳ kinh, ngày dễ mang thai và các mốc dự đoán trên cùng một lịch.'
              : 'Ghi nhận ngày bắt đầu kỳ kinh gần nhất để Yên ước tính chu kỳ và các mốc quan trọng.'}
          </p>
          {hasData && <CycleProgressBar prediction={prediction} />}
        </div>

        <div className="cycle-hero__visual">
          <div className="cycle-hero__ring" style={{ '--cycle-progress': cyclePercentage }}>
            <span>
              <small>{hasData ? 'Ngày' : 'Chu kỳ'}</small>
              <strong>{hasData ? cycleDay : '—'}</strong>
              <em>{hasData ? `/ ${cycleLength}` : 'Chưa có dữ liệu'}</em>
            </span>
          </div>
        </div>

        {hasData && (
          <div className="cycle-hero__highlights">
            <article>
              <CalendarIcon width={17} height={17} />
              <span><small>Kỳ tiếp theo</small><strong>{daysUntilNextPeriod != null && daysUntilNextPeriod >= 0 ? `Còn ${daysUntilNextPeriod} ngày` : 'Đang đến dự kiến'}</strong></span>
            </article>
            <article>
              <Sparkle width={17} height={17} />
              <span><small>Ngày dễ mang thai</small><strong>{formatShortRange(prediction?.fertile_window_start, prediction?.fertile_window_end)}</strong></span>
            </article>
          </div>
        )}
      </section>

      <div className={`cycle-dashboard ${hasData ? '' : 'cycle-dashboard--empty'}`}>
        {hasData ? (
          <section className="cycle-grid-panel">
            <div className="cycle-grid-panel__head">
              <div>
                <span>Lịch chu kỳ</span>
                <h2>Tháng {cursor.getMonth() + 1}, {cursor.getFullYear()}</h2>
              </div>
              <div className="cycle-grid-panel__nav">
                <button type="button" onClick={() => moveMonth(-1)} aria-label="Tháng trước">‹</button>
                <button type="button" onClick={jumpToToday}>Hôm nay</button>
                <button type="button" onClick={() => moveMonth(1)} aria-label="Tháng sau">›</button>
              </div>
            </div>

            <div className="cycle-grid__weekdays">
              {WEEKDAYS.map((weekday) => <span key={weekday}>{weekday}</span>)}
            </div>
            <div className="cycle-grid__cells">
              {grid.map(({ date, inMonth }) => {
                const iso = toISODate(date)
                const kind = classifyDay(iso, entries, prediction)
                const isToday = iso === todayIso
                const isOvulation = iso === prediction?.ovulation_date
                const isSelected = iso === selectedDate
                return (
                  <button
                    type="button"
                    key={iso}
                    className={`cycle-grid__cell cycle-grid__cell--${kind} ${!inMonth ? 'is-muted' : ''} ${isToday ? 'is-today' : ''} ${isOvulation ? 'is-ovulation' : ''} ${isSelected ? 'is-selected' : ''}`}
                    title={PHASE_META[kind].label}
                    aria-label={`${formatVi(iso)}: ${PHASE_META[kind].label}`}
                    aria-pressed={isSelected}
                    onClick={() => selectDay(date, inMonth)}
                  >
                    <span>{date.getDate()}</span>
                    {isToday && <small>Hôm nay</small>}
                    {isOvulation && !isToday && <small>Rụng trứng</small>}
                    {isOvulation && <i className="cycle-grid__ovulation" title="Ngày rụng trứng ước tính" />}
                  </button>
                )
              })}
            </div>

            <div className={`cycle-day-detail cycle-day-detail--${selectedKind}`} style={{ '--cycle-day-color': selectedMeta?.color }}>
              <span className="cycle-day-detail__icon"><SelectedDayIcon width={19} height={19} /></span>
              <div className="cycle-day-detail__body">
                <small>{selectedIsToday ? 'Hôm nay' : 'Ngày đã chọn'}</small>
                <strong>{formatVi(selectedDate)} · {selectedMeta?.label}</strong>
                <p>{selectedMeta?.description}</p>
                <div className="cycle-day-detail__tags">
                  {selectedCycleDay >= 1 && selectedCycleDay <= Math.max(cycleLength, 35) && <span>Ngày {selectedCycleDay} của chu kỳ</span>}
                  {selectedIsOvulation && <span>Rụng trứng ước tính</span>}
                  {selectedEntry?.note && <span>Ghi chú: {selectedEntry.note}</span>}
                </div>
              </div>
            </div>

            <div className="cycle-legend">
              <span className="cycle-legend__item"><i className="cycle-grid__dot--period" /> Ngày hành kinh</span>
              <span className="cycle-legend__item"><i className="cycle-grid__dot--period-predicted" /> Dự đoán kỳ tới</span>
              <span className="cycle-legend__item"><i className="cycle-grid__dot--fertile" /> Ngày dễ mang thai</span>
              <span className="cycle-legend__item"><i className="cycle-grid__dot--ovulation" /> Rụng trứng ước tính</span>
              <span className="cycle-legend__item"><i className="cycle-grid__dot--safe" /> Ngày an toàn (ước lượng)</span>
            </div>

            <div className="cycle-disclaimer">
              <Info width={14} height={14} />
              <span>
                Các mốc chỉ là ước lượng từ dữ liệu đã ghi nhận và có thể lệch nếu chu kỳ không đều.
                <strong> Không dùng kết quả này như một biện pháp tránh thai.</strong>
              </span>
            </div>
          </section>
        ) : (
          <section className="cycle-empty-card">
            <span><Droplet width={28} height={28} /></span>
            <h2>Bắt đầu theo dõi chu kỳ</h2>
            <p>Sau lần ghi nhận đầu tiên, bạn sẽ thấy lịch dự đoán, ngày dễ mang thai và ngày rụng trứng ước tính tại đây.</p>
            <ul>
              <li><i /> Dự đoán kỳ kinh tiếp theo</li>
              <li><i /> Theo dõi ngày dễ mang thai</li>
              <li><i /> Lưu lại ghi chú triệu chứng</li>
            </ul>
          </section>
        )}

        <aside className="cycle-sidebar">
          {hasData && (
            <section className="cycle-insights-card">
              <div className="cycle-section-heading">
                <span><Sparkle width={15} height={15} /> Các mốc dự đoán</span>
              </div>
              <div className="cycle-stats">
                <article className="cycle-stat cycle-stat--last">
                  <span className="cycle-stat__icon"><Droplet width={16} height={16} /></span>
                  <div className="cycle-stat__body"><small>Kỳ gần nhất</small><strong>{formatVi(prediction?.last_period_start_date)}</strong></div>
                </article>
                <article className="cycle-stat cycle-stat--next">
                  <span className="cycle-stat__icon"><CalendarIcon width={16} height={16} /></span>
                  <div className="cycle-stat__body"><small>Dự đoán kỳ tới</small><strong>{formatVi(prediction?.predicted_period_start)}</strong></div>
                </article>
                <article className="cycle-stat cycle-stat--ovulation">
                  <span className="cycle-stat__icon"><Sparkle width={16} height={16} /></span>
                  <div className="cycle-stat__body"><small>Rụng trứng ước tính</small><strong>{formatVi(prediction?.ovulation_date)}</strong></div>
                </article>
                <article className="cycle-stat cycle-stat--fertile">
                  <span className="cycle-stat__icon"><Heart width={16} height={16} /></span>
                  <div className="cycle-stat__body"><small>Ngày dễ mang thai</small><strong>{formatShortRange(prediction?.fertile_window_start, prediction?.fertile_window_end)}</strong></div>
                </article>
              </div>
            </section>
          )}

          <section className="cycle-record-card">
            <div className="cycle-section-heading">
              <span><Droplet width={15} height={15} /> Ghi nhận kỳ kinh</span>
              <small>Cập nhật để dự đoán chính xác hơn</small>
            </div>
            <form className="cycle-form" onSubmit={addEntry}>
              <label>
                <span>Ngày bắt đầu kỳ kinh</span>
                <input type="date" value={newDate} onChange={(event) => setNewDate(event.target.value)} max={todayIso} required />
              </label>
              <label>
                <span>Ghi chú (tuỳ chọn)</span>
                <input type="text" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Ví dụ: đau bụng nhẹ" />
              </label>
              <button className="btn btn--primary" type="submit" disabled={busy}>{busy ? 'Đang lưu…' : 'Ghi nhận chu kỳ'}</button>
            </form>
            {error && <p className="auth-error">{error}</p>}
          </section>

          <section className="cycle-history-card">
            <div className="cycle-section-heading">
              <span><CalendarIcon width={15} height={15} /> Lịch sử ghi nhận</span>
              <small>{entries.length} lần ghi nhận</small>
            </div>
            <ul className="cycle-history">
              {entries.length === 0 && <li className="empty-hint">Chưa có dữ liệu chu kỳ nào.</li>}
              {entries.map((entry) => (
                <li key={entry.id}>
                  <span className="cycle-history__icon"><Droplet width={14} height={14} /></span>
                  <span className="cycle-history__body">
                    <span className="cycle-history__date">{formatVi(entry.period_start_date)}</span>
                    <span className="cycle-history__note">{entry.note || 'Không có ghi chú'}</span>
                  </span>
                  <button type="button" className="cycle-history__remove" onClick={() => removeEntry(entry.id)} disabled={busy} aria-label="Xoá ghi nhận">
                    <X width={13} height={13} />
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </div>
  )
}
