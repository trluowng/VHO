/* Minimal stroke icons — 1.6 weight, rounded, drawn to match the calm aesthetic. */
const S = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round', strokeLinejoin: 'round' }

export const Cross = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M12 5v14M5 12h14" /></svg>
)
export const Send = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M5 12l14-7-6 14-2.5-5.5L5 12z" /></svg>
)
export const Microphone = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <rect {...S} x="9" y="3" width="6" height="11" rx="3" />
    <path {...S} d="M6.5 11.5a5.5 5.5 0 0 0 11 0M12 17v4M8.5 21h7" />
  </svg>
)
export const Restart = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M4 12a8 8 0 1 0 2.5-5.8M4 4v3.5H7.5" /></svg>
)
export const Info = (p) => (
  <svg viewBox="0 0 24 24" {...p}><circle {...S} cx="12" cy="12" r="9" /><path {...S} d="M12 11v5M12 7.6v.2" /></svg>
)
export const Shield = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" /><path {...S} d="M9 12l2 2 4-4" /></svg>
)
export const Phone = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M6.5 4h3l1.5 4-2 1.5a11 11 0 0 0 5.5 5.5L16 13l4 1.5v3a2 2 0 0 1-2.2 2A15.5 15.5 0 0 1 4.5 6.2 2 2 0 0 1 6.5 4z" /></svg>
)
export const Alert = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M12 4l9 16H3l9-16z" /><path {...S} d="M12 10v4M12 17.4v.2" /></svg>
)
export const Pulse = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M3 12h4l2-5 3 10 2.5-7 1.5 2h5" /></svg>
)
export const Stethoscope = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path {...S} d="M6 3v5a4 4 0 0 0 8 0V3" />
    <path {...S} d="M10 12v3a5 5 0 0 0 10 0v-2" />
    <circle {...S} cx="20" cy="11" r="2" />
  </svg>
)
export const Sit = (p) => (
  <svg viewBox="0 0 24 24" {...p}><circle {...S} cx="12" cy="5.5" r="2.2" /><path {...S} d="M8 21l1.5-7L7 11M16 21l-1.5-7L17 11M9.5 13.5h5" /></svg>
)
export const NoCar = (p) => (
  <svg viewBox="0 0 24 24" {...p}><circle {...S} cx="12" cy="12" r="9" /><path {...S} d="M5.6 5.6l12.8 12.8" /></svg>
)
export const Wind = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M3 8h11a2.5 2.5 0 1 0-2.5-2.5M3 12h15a2.5 2.5 0 1 1-2.5 2.5M3 16h9a2 2 0 1 1-2 2" /></svg>
)
export const ArrowRight = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M5 12h13M13 6l6 6-6 6" /></svg>
)
export const Calendar = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <rect {...S} x="3.5" y="5" width="17" height="16" rx="3" />
    <path {...S} d="M3.5 10h17M8 3v4M16 3v4" />
  </svg>
)
export const Droplet = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M12 3s6.5 7.2 6.5 11.5A6.5 6.5 0 1 1 5.5 14.5C5.5 10.2 12 3 12 3z" /></svg>
)
export const Chat = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path {...S} d="M4 5.5h16v11H9l-4 3.5v-3.5H4v-11z" />
  </svg>
)
export const LogOut = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path {...S} d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3M15 16l4-4-4-4M19 12H9" />
  </svg>
)
export const Watch = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <circle {...S} cx="12" cy="12" r="6.5" />
    <path {...S} d="M12 9v3.2l2 1.3M9.5 4h5l-.6 3h-3.8L9.5 4zM9.5 20h5l-.6-3h-3.8l-.6 3z" />
  </svg>
)
export const User = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <circle {...S} cx="12" cy="8.5" r="3.5" />
    <path {...S} d="M5 20c0-3.9 3.1-6.5 7-6.5s7 2.6 7 6.5" />
  </svg>
)
export const Sparkle = (p) => (
  <svg viewBox="0 0 24 24" fill="currentColor" {...p}>
    <path d="M12 3l1.8 5.6L19.5 10.4l-5.7 1.8L12 18l-1.8-5.8L4.5 10.4l5.7-1.8L12 3zM19 15.5l.9 2.7 2.7.9-2.7.9-.9 2.7-.9-2.7-2.7-.9 2.7-.9.9-2.7z" />
  </svg>
)
export const Clock = (p) => (
  <svg viewBox="0 0 24 24" {...p}><circle {...S} cx="12" cy="12" r="9" /><path {...S} d="M12 7v5l3.5 2" /></svg>
)
export const Check = (p) => (
  <svg viewBox="0 0 24 24" {...p}><circle {...S} cx="12" cy="12" r="9" /><path {...S} d="M8 12.3l2.6 2.6L16 9.5" /></svg>
)
export const Heart = (p) => (
  <svg viewBox="0 0 24 24" fill="currentColor" {...p}>
    <path d="M12 20.2s-7.4-4.6-9.9-9.1C.5 7.7 1.8 4.3 5 3.4c2-.6 4 .2 5 1.9 1-1.7 3-2.5 5-1.9 3.2.9 4.5 4.3 2.9 7.7-2.5 4.5-9.9 9.1-9.9 9.1z" />
  </svg>
)
export const Smile = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <circle {...S} cx="12" cy="12" r="9" />
    <path {...S} d="M8.3 13.5c1 1.4 2.2 2.1 3.7 2.1s2.7-.7 3.7-2.1" />
    <path {...S} d="M9 10v.2M15 10v.2" />
  </svg>
)
export const Leaf = (p) => (
  <svg viewBox="0 0 24 24" fill="currentColor" {...p}>
    <path d="M4 20c0-9 6.5-15.5 16-16 .3 9.5-6 16-15 16-.4 0-.7 0-1 0z" />
    <path fill="none" stroke="rgba(255,255,255,0.55)" strokeWidth="1.2" strokeLinecap="round" d="M6.5 18C11 13.5 14.5 10 17.5 6" />
  </svg>
)
export const Quiz = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <circle {...S} cx="12" cy="12" r="9" />
    <path {...S} d="M9.5 9.2a2.5 2.5 0 1 1 3.3 2.4c-.8.3-1.3 1-1.3 1.9v.3M12 17v.2" />
  </svg>
)
export const TestTube = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path {...S} d="M9 3h6M9.5 3.5v13a2.5 2.5 0 0 0 5 0v-13" />
    <path {...S} d="M9.5 13h5" />
  </svg>
)
export const Pill = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <rect {...S} x="3.5" y="9.5" width="17" height="7" rx="3.5" transform="rotate(-35 12 13)" />
    <path {...S} d="M12 8.6l3.4 3.4" />
  </svg>
)
export const Syringe = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path {...S} d="M20.5 3.5l-2.3 2.3M17 7l-9.5 9.5-3.5 4 4-3.5L17.5 7.5" />
    <path {...S} d="M14.5 5.5l4 4M12.5 7.5l2 2M10.5 9.5l2 2" />
  </svg>
)
export const Bell = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path {...S} d="M6 10a6 6 0 0 1 12 0c0 4 1.5 5.5 1.5 5.5h-15S6 14 6 10z" />
    <path {...S} d="M9.5 18.5a2.5 2.5 0 0 0 5 0" />
  </svg>
)
export const ChevronRight = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M9 5l7 7-7 7" /></svg>
)
export const ChevronDown = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M5 9l7 7 7-7" /></svg>
)
export const MapPin = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path {...S} d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12z" />
    <circle {...S} cx="12" cy="9" r="2.4" />
  </svg>
)
export const RefreshCw = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path {...S} d="M4 12a8 8 0 0 1 14-5.3M20 12a8 8 0 0 1-14 5.3" />
    <path {...S} d="M18 3v4h-4M6 21v-4h4" />
  </svg>
)
export const Filter = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M4 5h16M7 12h10M10 19h4" /></svg>
)
export const Edit = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path {...S} d="M15.5 4.5l4 4L8 20H4v-4l11.5-11.5z" />
  </svg>
)
export const X = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M6 6l12 12M18 6L6 18" /></svg>
)
export const Camera = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <path {...S} d="M4 8h3l1.5-2h7L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z" />
    <circle {...S} cx="12" cy="13.5" r="3.4" />
  </svg>
)
export const Search = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <circle {...S} cx="10.5" cy="10.5" r="6.5" />
    <path {...S} d="M20 20l-4.5-4.5" />
  </svg>
)
