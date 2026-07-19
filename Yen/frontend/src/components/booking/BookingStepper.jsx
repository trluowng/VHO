import { Check } from '../icons.jsx'

const STEPS = [
  { number: 1, label: 'Chọn bác sĩ', hint: 'Chuyên khoa phù hợp' },
  { number: 2, label: 'Chọn lịch khám', hint: 'Ngày và khung giờ' },
  { number: 3, label: 'Xác nhận', hint: 'Kiểm tra thông tin' },
]

export default function BookingStepper({ current = 1, complete = false }) {
  return (
    <ol className="booking-stepper" aria-label="Các bước đặt lịch khám">
      {STEPS.map((step) => {
        const isDone = complete || step.number < current
        const isActive = !complete && step.number === current
        return (
          <li
            key={step.number}
            className={`${isDone ? 'is-done' : ''} ${isActive ? 'is-active' : ''}`.trim()}
            aria-current={isActive ? 'step' : undefined}
          >
            <span className="booking-stepper__number">
              {isDone ? <Check width={14} height={14} /> : step.number}
            </span>
            <span className="booking-stepper__copy">
              <strong>{step.label}</strong>
              <small>{step.hint}</small>
            </span>
          </li>
        )
      })}
    </ol>
  )
}
