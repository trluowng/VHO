/* Minh hoạ ống nghe y tế vẽ tay bằng SVG — ống màu teal có gradient, đầu nghe
   kim loại bạc có bóng đổ, giống tông màu/chất liệu trong ảnh tham chiếu.
   Tách thành component riêng: sau này muốn thay bằng ảnh chụp thật chỉ cần
   đổi nội dung file này, không đụng vào HealthIllustration. */
export default function StethoscopeArt({ className }) {
  return (
    <svg viewBox="0 0 200 200" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="steth-tube" x1="20" y1="10" x2="180" y2="190" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#35A7BB" />
          <stop offset="100%" stopColor="#07899A" />
        </linearGradient>
        <radialGradient id="steth-metal" cx="35%" cy="30%" r="75%">
          <stop offset="0%" stopColor="#F5F8F9" />
          <stop offset="55%" stopColor="#C7D2D6" />
          <stop offset="100%" stopColor="#8B9AA0" />
        </radialGradient>
        <radialGradient id="steth-metal-sm" cx="35%" cy="30%" r="75%">
          <stop offset="0%" stopColor="#F5F8F9" />
          <stop offset="60%" stopColor="#B7C2C6" />
          <stop offset="100%" stopColor="#79888E" />
        </radialGradient>
      </defs>

      {/* Ống dẫn từ hai tai nghe hội tụ xuống đầu nghe */}
      <path
        d="M53 44 C53 68, 60 78, 74 87 C90 97, 97 98, 100 112"
        stroke="url(#steth-tube)" strokeWidth="9" strokeLinecap="round"
      />
      <path
        d="M147 44 C147 68, 140 78, 126 87 C110 97, 103 98, 100 112"
        stroke="url(#steth-tube)" strokeWidth="9" strokeLinecap="round"
      />
      <path
        d="M100 112 C100 122, 100 130, 100 139"
        stroke="url(#steth-tube)" strokeWidth="9" strokeLinecap="round"
      />

      {/* Hai tai nghe kim loại */}
      <rect x="46" y="17" width="13" height="27" rx="6.5" fill="url(#steth-metal-sm)" transform="rotate(-13 52.5 30.5)" />
      <rect x="141" y="17" width="13" height="27" rx="6.5" fill="url(#steth-metal-sm)" transform="rotate(13 147.5 30.5)" />

      {/* Đầu nghe (diaphragm) */}
      <circle cx="100" cy="168" r="31" fill="url(#steth-metal)" />
      <circle cx="100" cy="168" r="21.5" fill="none" stroke="#8B9AA0" strokeWidth="2.5" />
      <ellipse cx="89" cy="156" rx="9" ry="5" fill="#ffffff" opacity="0.6" />
    </svg>
  )
}
