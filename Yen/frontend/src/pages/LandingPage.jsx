import { PhoneCall, ShieldAlert, Stethoscope, Watch, HelpCircle, Calendar } from 'lucide-react'
import Header from '../components/landing/Header.jsx'
import HeroSection from '../components/landing/HeroSection.jsx'
import FeatureCard from '../components/landing/FeatureCard.jsx'

const FEATURES = [
  {
    icon: Stethoscope,
    iconBg: 'bg-skytint-bg',
    iconColor: 'text-cyan',
    status: 'Đã có',
    title: 'Tra cứu giá & dịch vụ',
    desc: 'Hỏi nhanh bảng giá dịch vụ kỹ thuật, xét nghiệm và gói khám tại viện.',
  },
  {
    icon: Watch,
    iconBg: 'bg-rose-50',
    iconColor: 'text-rose-500',
    status: 'Đã có',
    title: 'Hướng dẫn quy trình khám',
    desc: 'Chuẩn bị giấy tờ, quy trình BHYT và các bước đến khám tại bệnh viện.',
  },
  {
    icon: HelpCircle,
    iconBg: 'bg-violet-50',
    iconColor: 'text-violet-500',
    status: 'Đã có',
    title: 'Hỗ trợ khách hàng 24/7',
    desc: 'Giải đáp thắc mắc về dịch vụ, đặt lịch và quyền lợi người bệnh.',
  },
  {
    icon: Calendar,
    iconBg: 'bg-statusgreen-bg',
    iconColor: 'text-statusgreen',
    status: 'Đã có',
    title: 'Lịch khám & lời nhắc',
    desc: 'Nhắc lịch khám, tái khám và theo dõi sức khỏe tim mạch định kỳ.',
  },
]

export default function LandingPage() {
  return (
    <div className="relative h-[100dvh] overflow-y-auto bg-gradient-to-br from-white via-white to-skytint-bg">
      <Header />
      <HeroSection />

      <section className="relative z-10 mx-auto grid w-full max-w-[1600px] grid-cols-1 gap-5 px-6 pb-14 sm:grid-cols-2 sm:px-10 lg:grid-cols-4 lg:px-10 xl:px-16">
        {FEATURES.map((f) => (
          <FeatureCard key={f.title} {...f} />
        ))}
      </section>

      <section className="relative z-10 mx-auto mb-10 flex w-full max-w-[900px] items-center gap-4 rounded-[20px] bg-gradient-to-r from-teal to-teal-deep px-8 py-5 text-white shadow-[0_18px_40px_rgba(7,137,154,0.28)] sm:px-10">
        <PhoneCall className="h-7 w-7 shrink-0" strokeWidth={1.8} />
        <p className="m-0 text-[14px] leading-relaxed">
          Khi phát hiện dấu hiệu khẩn cấp (đau ngực dữ dội, khó thở, đột quỵ...), Yên bỏ qua mọi
          bước hỏi đáp và hướng dẫn gọi <strong>115</strong> hoặc đến khoa Cấp cứu Bệnh viện Tim Hà Nội ngay lập tức.
        </p>
      </section>

      <footer className="relative z-10 mx-auto w-full max-w-[680px] px-6 pb-14 text-center sm:px-10">
        <div className="flex items-start justify-center gap-2.5 text-[11.5px] leading-relaxed text-slate-text">
          <ShieldAlert className="h-4 w-4 flex-none translate-y-[1px] text-slate-text" strokeWidth={1.8} />
          <span>
            Yên là trợ lý hỗ trợ khách hàng của Bệnh viện Tim Hà Nội, <strong className="text-navy">không thay thế chẩn đoán y khoa</strong>.
            Khi nghi ngờ, hãy liên hệ nhân viên y tế của bệnh viện.
          </span>
        </div>
      </footer>
    </div>
  )
}
