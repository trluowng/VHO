import { useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { Cross, Calendar as CalendarIcon, Droplet } from '../components/icons.jsx'
import TabNav from '../components/TabNav.jsx'
import HealthCalendar from '../components/HealthCalendar.jsx'
import CycleTracker from '../components/CycleTracker.jsx'

export default function CalendarPage() {
  const { isFemale } = useAuth()
  const [subTab, setSubTab] = useState('calendar') // 'calendar' | 'cycle'

  return (
    <>
      <div className="atmos">
        <div className="atmos__grain" />
        <div className="atmos__veil" />
      </div>

      <div className="shell">
        <header className="topbar">
          <div className="brand">
            <div className="brand__mark"><Cross /></div>
            <div>
              <div className="brand__name">An<em> · sức khỏe</em></div>
              <div className="brand__sub">Lịch theo dõi sức khỏe</div>
            </div>
          </div>
          <TabNav />
        </header>

        {isFemale && (
          <div className="subtabs">
            <button
              className={`subtabs__btn ${subTab === 'calendar' ? 'is-active' : ''}`}
              onClick={() => setSubTab('calendar')}
            >
              <CalendarIcon width={16} height={16} /> Lịch sức khỏe
            </button>
            <button
              className={`subtabs__btn ${subTab === 'cycle' ? 'is-active' : ''}`}
              onClick={() => setSubTab('cycle')}
            >
              <Droplet width={16} height={16} /> Chu kỳ kinh nguyệt
            </button>
          </div>
        )}

        <div className="calendar-page__body">
          {subTab === 'cycle' && isFemale ? <CycleTracker /> : <HealthCalendar />}
        </div>
      </div>
    </>
  )
}
