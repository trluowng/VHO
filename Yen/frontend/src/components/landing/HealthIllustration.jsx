import { Smile, Heart, Activity, ShieldCheck, MessageCircle } from 'lucide-react'
import stethoscopePhoto from '../../assets/landing/stethoscope.png'

/* Minh hoạ bên phải hero. Ảnh ống nghe (nền trong suốt, đã có sẵn đế đá +
   lá cây) đặt trực tiếp — muốn đổi ảnh khác thì chỉ cần thay file trong
   src/assets/landing/stethoscope.png, không đụng vào phần còn lại. */
export default function HealthIllustration() {
  return (
    <div className="relative mx-auto h-[420px] w-full max-w-[560px] overflow-visible lg:mx-0 xl:h-[460px] xl:max-w-[640px]" aria-hidden="true">
      {/* Khối oval bo cong lớn phía sau */}
      <div className="absolute inset-[2%_2%_-2%_10%] rounded-[46%_54%_60%_40%/48%_42%_58%_52%] bg-gradient-to-br from-skytint-bg via-[#DCEFFB] to-white shadow-[0_30px_70px_rgba(16,42,92,0.14)]" />

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

      {/* Ảnh ống nghe thật (đế đá + lá cây đã có sẵn trong ảnh), tràn nhẹ ra góc dưới-phải */}
      <img
        src={stethoscopePhoto}
        alt="Ống nghe y tế đặt trên đế đá cẩm thạch"
        className="absolute bottom-[-16px] right-[-8%] w-[420px] max-w-[78%] drop-shadow-[0_20px_40px_rgba(16,42,92,0.18)] sm:max-w-[460px]"
      />
    </div>
  )
}
