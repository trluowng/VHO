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
    title: 'Tư vấn triệu chứng AI',
    desc: 'Hỏi đáp triệu chứng bằng hội thoại tự nhiên, chính xác và dễ hiểu.',
  },
  {
    icon: Watch,
    iconBg: 'bg-rose-50',
    iconColor: 'text-rose-500',
    status: 'Đã có',
    title: 'Giám sát sức khỏe mỗi ngày',
    desc: 'Theo dõi chỉ số, nhắc lịch uống thuốc và cảnh báo bất thường.',
  },
  {
    icon: HelpCircle,
    iconBg: 'bg-violet-50',
    iconColor: 'text-violet-500',
    status: 'Đã có',
    title: 'Quản lý sức khỏe tổng thể',
    desc: 'Lưu trữ hồ sơ, lịch sử bệnh và gợi ý chăm sóc cá nhân hóa.',
  },
  {
    icon: Calendar,
    iconBg: 'bg-statusgreen-bg',
    iconColor: 'text-statusgreen',
    status: 'Đã có',
    title: 'Lịch khám & lời nhắc',
    desc: 'Nhắc lịch khám, tiêm chủng, tái khám và chăm sóc định kỳ.',
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
          bước hỏi đáp và hướng dẫn gọi <strong>115</strong> ngay lập tức.
        </p>
      </section>

      <footer className="relative z-10 mx-auto w-full max-w-[680px] px-6 pb-14 text-center sm:px-10">
        <div className="flex items-start justify-center gap-2.5 text-[11.5px] leading-relaxed text-slate-text">
          <ShieldAlert className="h-4 w-4 flex-none translate-y-[1px] text-slate-text" strokeWidth={1.8} />
          <span>
            Yên là công cụ hỗ trợ phân loại mức độ khẩn cấp, <strong className="text-navy">không thay thế chẩn đoán y khoa</strong>.
            Khi nghi ngờ, hãy liên hệ nhân viên y tế.
          </span>
        </div>
      </footer>
    </div>
  )
}
