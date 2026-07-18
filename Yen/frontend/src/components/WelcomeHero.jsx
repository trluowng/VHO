import { motion } from 'framer-motion'
import { ArrowRight } from './icons.jsx'

const EXAMPLES = [
  { icon: '📋', q: 'Bệnh viện có xét nghiệm siêu âm tim không, giá bao nhiêu?', tag: 'Tra cứu giá' },
  { icon: '🪪', q: 'Khám BHYT tại viện cần chuẩn bị giấy tờ gì?', tag: 'Quy trình' },
  { icon: '🫀', q: 'Tôi đau ngực và khó thở', tag: 'Khẩn cấp' },
]

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.15 } },
}
const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] } },
}

export default function WelcomeHero({ onPick }) {
  return (
    <motion.div className="hero" variants={container} initial="hidden" animate="show">
      <motion.div className="hero__eyebrow" variants={item}>
        Trợ lý Bệnh viện Tim Hà Nội
      </motion.div>
      <motion.h1 className="hero__title" variants={item}>
        Hỏi đáp dịch vụ, giá khám & <em>hỗ trợ</em> tại viện
      </motion.h1>
      <motion.p className="hero__lede" variants={item}>
        Tra cứu giá dịch vụ, hướng dẫn quy trình khám BHYT, đặt lịch hay mô tả triệu chứng — mình
        sẽ hướng dẫn bạn <strong>bước tiếp theo phù hợp</strong> tại Bệnh viện Tim Hà Nội.
      </motion.p>
      <motion.div className="hero__examples" variants={item}>
        {EXAMPLES.map((ex) => (
          <button key={ex.q} className="example-card" onClick={() => onPick(ex.q)}>
            <span className="example-card__ic">{ex.icon}</span>
            <span className="example-card__tx">
              <span className="example-card__q">"{ex.q}"</span>
              <span className="example-card__t">{ex.tag}</span>
            </span>
            <ArrowRight className="example-card__arrow" width={18} height={18} />
          </button>
        ))}
      </motion.div>
    </motion.div>
  )
}
