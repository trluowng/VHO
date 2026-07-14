/* Minimal stroke icons — 1.6 weight, rounded, drawn to match the calm aesthetic. */
const S = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round', strokeLinejoin: 'round' }

export const Cross = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M12 5v14M5 12h14" /></svg>
)
export const Send = (p) => (
  <svg viewBox="0 0 24 24" {...p}><path {...S} d="M5 12l14-7-6 14-2.5-5.5L5 12z" /></svg>
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
export const Quiz = (p) => (
  <svg viewBox="0 0 24 24" {...p}>
    <circle {...S} cx="12" cy="12" r="9" />
    <path {...S} d="M9.5 9.2a2.5 2.5 0 1 1 3.3 2.4c-.8.3-1.3 1-1.3 1.9v.3M12 17v.2" />
  </svg>
)
