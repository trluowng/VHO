import { Link } from 'react-router-dom'
import { MessageCircle } from 'lucide-react'

export default function Header() {
  return (
    <header className="relative z-10 mx-auto flex w-full max-w-[1600px] items-center justify-between gap-3 px-4 py-4 sm:gap-4 sm:px-10 sm:py-6 lg:px-16">
      <div className="flex min-w-0 items-center gap-2.5 sm:gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[14px] bg-gradient-to-br from-cyan to-teal-deep text-white shadow-[0_10px_22px_rgba(17,167,167,0.28)] sm:h-[52px] sm:w-[52px] sm:rounded-[16px]">
          <span className="text-[20px] font-light leading-none sm:text-[26px]">+</span>
        </div>
        <div className="min-w-0">
          <p className="whitespace-nowrap font-serif text-[16px] leading-none text-navy sm:text-[22px]">
            <span className="font-semibold">Yên</span>{' '}
            <span className="italic text-teal-deep">· sức khỏe</span>
          </p>
          <p className="mt-[4px] hidden whitespace-nowrap text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-text/75 sm:mt-[6px] sm:block">
            AI Y tế cá nhân
          </p>
        </div>
      </div>

      <nav className="flex shrink-0 items-center gap-2 sm:gap-3">
        <Link
          to="/app"
          className="inline-flex h-[44px] items-center gap-1.5 rounded-[14px] bg-gradient-to-r from-teal to-teal-deep px-4 text-[13px] font-semibold text-white shadow-[0_10px_24px_rgba(7,137,154,0.28)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_14px_28px_rgba(7,137,154,0.34)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan sm:h-[54px] sm:gap-2 sm:px-5 sm:text-[14px]"
        >
          <MessageCircle className="h-3.5 w-3.5 sm:h-4 sm:w-4" strokeWidth={2} />
          Mở Yên
        </Link>
      </nav>
    </header>
  )
}
