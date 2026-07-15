import { Smile, Heart, Activity, ShieldCheck, MessageCircle, Leaf } from 'lucide-react'
import StethoscopeArt from './StethoscopeArt.jsx'

/* Minh hoạ bên phải hero. Ảnh ống nghe hiện là icon Lucide dựng lớn trên khối
   bo cong — tách riêng ở đây để sau này thay bằng ảnh chụp thật chỉ cần đổi
   khối <div className="stethoscope-plate"> bên dưới, không đụng vào phần còn lại. */
export default function HealthIllustration() {
  return (
    <div className="relative mx-auto h-[420px] w-full max-w-[560px] xl:mx-0" aria-hidden="true">
      {/* Khối oval bo cong lớn phía sau */}
      <div className="absolute inset-[4%_8%] rounded-[46%_54%_60%_40%/48%_42%_58%_52%] bg-gradient-to-br from-skytint-bg via-[#DCEFFB] to-white shadow-[0_30px_70px_rgba(16,42,92,0.14)]" />

      {/* Thẻ hội thoại nổi */}
      <div className="absolute left-1/2 top-[6%] w-[240px] -translate-x-[46%] rounded-[20px] bg-white py-4 pl-4 pr-8 shadow-[0_18px_40px_rgba(16,42,92,0.16)] animate-float-soft sm:left-auto sm:right-[-4%] sm:translate-x-0">
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
      <div className="absolute right-[8%] top-[46%] flex gap-2.5 animate-float-soft-slow [animation-delay:0.4s]">
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

      {/* Bề mặt trắng bo cong + minh hoạ ống nghe, góc dưới-phải */}
      <div className="stethoscope-plate absolute bottom-0 right-[2%] flex h-[190px] w-[230px] items-center justify-center rounded-[50%_50%_46%_54%/54%_54%_46%_46%] bg-white shadow-[0_24px_50px_rgba(16,42,92,0.16)]">
        <StethoscopeArt className="h-[120px] w-[120px]" />
      </div>

      {/* Vài chiếc lá xanh nhạt cạnh khối ống nghe */}
      <Leaf className="absolute bottom-[6%] right-[38%] h-8 w-8 text-teal/70 animate-leaf-sway [transform-origin:50%_100%]" strokeWidth={1.6} />
      <Leaf className="absolute bottom-[-2%] right-[30%] h-6 w-6 -scale-x-100 text-teal-deep/60 animate-leaf-sway [animation-delay:0.6s] [transform-origin:50%_100%]" strokeWidth={1.6} />
    </div>
  )
}
