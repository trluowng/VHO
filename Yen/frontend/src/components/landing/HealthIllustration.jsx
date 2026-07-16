import { Smile, Heart, Activity, ShieldCheck, MessageCircle } from 'lucide-react'

/* Ảnh nền (vòm, ống nghe, lá cây) chỉ áp cho đúng khối minh hoạ này — không
   đặt lên cả HeroSection để tránh bị kéo giãn/lệch khi hero xếp chồng ở
   mobile. Thẻ hội thoại + icon chip nổi đè lên trên ảnh. */
export default function HealthIllustration() {
  return (
    <div
      className="relative mx-auto h-[360px] w-full max-w-[560px] overflow-hidden rounded-[32px] shadow-[0_30px_70px_rgba(16,42,92,0.14)] lg:mx-0 xl:h-[420px] xl:max-w-[620px]"
      aria-hidden="true"
    >
      <div className="absolute inset-0 bg-[url('/images/hero-bg.jpg')] bg-cover bg-[73%_42%]" />

      {/* Thẻ hội thoại nổi */}
      <div className="absolute left-1/2 top-[7%] w-[230px] -translate-x-[46%] rounded-[20px] bg-white py-4 pl-4 pr-8 shadow-[0_18px_40px_rgba(16,42,92,0.16)] animate-float-soft sm:left-auto sm:right-[4%] sm:translate-x-0">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-teal to-teal-deep text-white">
            <Smile className="h-5 w-5" strokeWidth={2} />
          </div>
          <div className="min-w-0">
            <p className="text-[13.5px] font-semibold leading-tight text-navy">Xin chào, tôi là Yên</p>
            <p className="mt-1 text-[12px] leading-snug text-slate-text">
              Tôi luôn sẵn sàng lắng nghe và hỗ trợ bạn 24/7
            </p>
          </div>
        </div>
        <Heart className="absolute right-3 top-4 h-4 w-4 text-teal" strokeWidth={2} />
      </div>

      {/* Ba nút vuông bo góc bên dưới thẻ hội thoại */}
      <div className="absolute right-[12%] top-[48%] flex gap-2.5 animate-float-soft-slow [animation-delay:0.4s]">
        <span className="flex h-11 w-11 items-center justify-center rounded-[13px] bg-white text-cyan shadow-[0_10px_22px_rgba(16,42,92,0.10)]">
          <Activity className="h-[18px] w-[18px]" strokeWidth={2} />
        </span>
        <span className="flex h-11 w-11 items-center justify-center rounded-[13px] bg-white text-teal-deep shadow-[0_10px_22px_rgba(16,42,92,0.10)]">
          <ShieldCheck className="h-[18px] w-[18px]" strokeWidth={2} />
        </span>
        <span className="flex h-11 w-11 items-center justify-center rounded-[13px] bg-white text-navy shadow-[0_10px_22px_rgba(16,42,92,0.10)]">
          <MessageCircle className="h-[18px] w-[18px]" strokeWidth={2} />
        </span>
      </div>
    </div>
  )
}
