import { Link } from 'react-router-dom'
import { Sparkles, ArrowRight, Clock, ShieldCheck, BadgeCheck, Heart } from 'lucide-react'
import HealthIllustration from './HealthIllustration.jsx'

export default function HeroSection() {
  return (
    <section className="relative z-10 mx-auto grid w-full max-w-[1600px] grid-cols-1 items-center gap-12 px-6 pb-16 pt-6 sm:px-10 lg:grid-cols-[52%_48%] lg:gap-8 lg:px-10 lg:pt-10 xl:gap-10 xl:px-16">
      <div className="mx-auto max-w-[650px] text-center lg:mx-0 lg:text-left">
        <span className="text-[14px] font-bold uppercase tracking-[0.2em] text-cyan sm:text-[15px]">
          Trợ lý y tế AI cá nhân
        </span>

        <h1 className="mt-5 font-serif text-[38px] font-normal leading-[1.14] tracking-tight text-navy sm:text-[44px] lg:text-[38px] xl:text-[48px] 2xl:text-[52px]">
          Chăm sóc sức khỏe <em className="whitespace-nowrap italic text-teal-deep">chủ động</em>,
          <br className="hidden lg:block" /> có mặt mọi lúc bạn cần
        </h1>

        <p className="mx-auto mt-6 max-w-[650px] text-[17px] leading-[1.7] text-slate-text lg:mx-0 lg:text-[16px] xl:text-[18px]">
          Yên tư vấn triệu chứng bằng hội thoại tự nhiên, ghi nhớ hồ sơ sức khỏe của riêng bạn để
          không phải hỏi lại từ đầu mỗi lần, và luôn ưu tiên tính mạng — phát hiện dấu hiệu khẩn
          cấp là hướng dẫn gọi 115 ngay lập tức.
        </p>

        <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center lg:justify-start">
          <Link
            to="/dang-ky"
            className="inline-flex h-[56px] w-full items-center justify-center gap-2 rounded-[16px] bg-gradient-to-r from-cyan to-teal-deep px-7 text-[15px] font-bold text-white shadow-[0_14px_30px_rgba(28,159,227,0.30)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_18px_36px_rgba(28,159,227,0.36)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan sm:w-auto whitespace-nowrap"
          >
            <Sparkles className="h-[18px] w-[18px]" strokeWidth={2} />
            Tạo tài khoản miễn phí
            <ArrowRight className="h-[18px] w-[18px]" strokeWidth={2} />
          </Link>
          <Link
            to="/dang-nhap"
            className="inline-flex h-[56px] w-full items-center justify-center gap-2 rounded-[16px] border border-skytint-border bg-white px-7 text-[15px] font-semibold text-navy shadow-[0_2px_8px_rgba(16,42,92,0.05)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_10px_22px_rgba(16,42,92,0.10)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan sm:w-auto whitespace-nowrap"
          >
            <Clock className="h-[17px] w-[17px]" strokeWidth={2} />
            Tôi đã có tài khoản
          </Link>
        </div>

        <div className="mt-7 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 lg:justify-start">
          <span className="inline-flex items-center gap-2 text-[13.5px] font-medium text-slate-text">
            <ShieldCheck className="h-[15px] w-[15px] text-cyan" strokeWidth={2} /> Bảo mật tuyệt đối
          </span>
          <span className="inline-flex items-center gap-2 text-[13.5px] font-medium text-slate-text">
            <BadgeCheck className="h-[15px] w-[15px] text-cyan" strokeWidth={2} /> Dễ sử dụng
          </span>
          <span className="inline-flex items-center gap-2 text-[13.5px] font-medium text-slate-text">
            <Heart className="h-[15px] w-[15px] text-cyan" strokeWidth={2} /> Đồng hành tin cậy
          </span>
        </div>
      </div>

      <HealthIllustration />
    </section>
  )
}
