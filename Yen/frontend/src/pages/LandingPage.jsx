import { PhoneCall, ShieldAlert, Stethoscope, Watch, HelpCircle, Calendar, Leaf } from 'lucide-react'
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
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -right-40 top-0 h-[600px] w-[600px] rounded-full bg-[radial-gradient(circle,rgba(28,159,227,0.14),transparent_70%)] blur-2xl" />

        {/* Lá cây mờ trang trí góc dưới-trái, giống ảnh tham chiếu */}
        <Leaf className="absolute bottom-[8%] left-[-2%] h-32 w-32 -rotate-12 text-cyan/10" strokeWidth={1} />
        <Leaf className="absolute bottom-[18%] left-[4%] h-20 w-20 rotate-[18deg] text-navy/10" strokeWidth={1} />
        <Leaf className="absolute bottom-[2%] left-[9%] h-16 w-16 -rotate-45 text-cyan/10" strokeWidth={1} />

        {/* Cụm lá xanh góc trên-phải, tràn nhẹ ra mép trang */}
        <Leaf className="absolute -right-6 top-[12%] h-28 w-28 rotate-[24deg] text-statusgreen/20" strokeWidth={1} />
        <Leaf className="absolute right-10 top-[22%] h-16 w-16 -rotate-12 text-teal/25" strokeWidth={1} />
      </div>

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
