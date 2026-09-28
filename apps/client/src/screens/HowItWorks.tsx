import type { ReactNode } from "react";
import SceneBackground from "../components/SceneBackground";
import { ArrowRight, Check } from "../components/icons";

function StepCard({
  n,
  title,
  desc,
  preview,
}: {
  n: number;
  title: string;
  desc: string;
  preview: ReactNode;
}) {
  return (
    <li className="flex gap-4">
      <div className="flex flex-col items-center">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full border border-[#27ffa1]/50 bg-[#27ffa1]/10 text-[13px] font-bold text-[#27ffa1]">
          {n}
        </span>
        {n < 4 && <span className="mt-2 w-px flex-1 bg-gradient-to-b from-[#27ffa1]/40 to-transparent" />}
      </div>
      <div className="flex flex-1 items-start justify-between gap-4 pb-8">
        <div className="min-w-0 flex-1">
          <h3 className="text-[13.5px] font-bold leading-tight text-white">{title}</h3>
          <p className="mt-0.5 text-[11px] leading-snug text-[#8fbaa4]">{desc}</p>
        </div>
        <div className="shrink-0">{preview}</div>
      </div>
    </li>
  );
}

export default function HowItWorks({ onBegin }: { onBegin: () => void }) {
  return (
    <div className="relative flex h-full w-full flex-col overflow-y-auto scene-scroll bg-[#04120b] text-white">
      <SceneBackground className="opacity-90" />
      <div className="pointer-events-none absolute inset-0 bg-[#030f09]/60" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-[#020c07] to-transparent" />

      <div className="relative flex flex-1 flex-col px-8 pb-7 pt-10">
        <h1
          className="leading-[0.95]"
          style={{ fontFamily: '"Geist:ExtraBold", sans-serif', fontWeight: 800, fontSize: 38, letterSpacing: "-1px" }}
        >
          <span className="text-white">Your work.</span>
          <br />
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage:
                "radial-gradient(ellipse at center, #5ffda1 0%, #5ffda1 56.731%, #86feca 78.365%, #adfff4 100%)",
              WebkitBackgroundClip: "text",
            }}
          >
            Our warm-up.
          </span>
        </h1>
        <p className="mt-2 max-w-[280px] text-[12px] leading-snug text-[#9cc4ae]">
          A few minutes to make it interesting. Then we lock the app and send you back to work.
        </p>

        <ol className="mt-11 flex-1">
          <StepCard
            n={1}
            title="Tell us what you're working on."
            desc="Enter a topic, task or subject."
            preview={
              <div className="w-[150px] rounded-xl border border-white/10 bg-white/[0.04] p-2 backdrop-blur-sm">
                <div className="flex items-center gap-1.5 rounded-lg bg-[#0c2a1c] px-2.5 py-1.5">
                  <span className="flex-1 text-[10.5px] text-[#cdeadd]">I need to study thermodynamics</span>
                  <span className="flex size-4 items-center justify-center rounded-full bg-[#27ffa1] text-[#04120b]">
                    <Check className="size-2.5" />
                  </span>
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {["Math", "Facts", "Chapter", "Concept"].map((t, i) => (
                    <span
                      key={t}
                      className={`rounded-full px-2 py-0.5 text-[9px] font-medium ${
                        i === 0 ? "bg-[#27ffa1] text-[#04120b]" : "border border-white/15 text-[#a9cdbc]"
                      }`}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            }
          />
          <StepCard
            n={2}
            title="Pick your time."
            desc="Choose 5, 10, 15 or 20 minutes."
            preview={
              <div className="flex gap-2">
                {["5 min", "10 min", "20 min"].map((t, i) => (
                  <span
                    key={t}
                    className={`rounded-xl px-3 py-2 text-[12px] font-semibold ${
                      i === 1
                        ? "bg-[#27ffa1] text-[#04120b]"
                        : "border border-white/12 bg-white/[0.04] text-[#c3e2d4]"
                    }`}
                  >
                    {t}
                  </span>
                ))}
              </div>
            }
          />
          <StepCard
            n={3}
            title="Get a personalized curiosity session."
            desc="We'll show you a mix of memes, facts, ideas, visuals and more, tailored to your topic."
            preview={
              <div className="relative h-[80px] w-[96px]">
                <div className="absolute left-0 top-2.5 h-[60px] w-[46px] -rotate-[12deg] overflow-hidden rounded-lg shadow-lg ring-1 ring-white/15">
                  <svg viewBox="0 0 46 60" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
                    <rect width="46" height="60" fill="#0c3a2a" />
                    <g fill="none" stroke="#27ffa1" strokeWidth="1.4" opacity="0.85">
                      <ellipse cx="23" cy="30" rx="16" ry="7" />
                      <ellipse cx="23" cy="30" rx="16" ry="7" transform="rotate(60 23 30)" />
                      <ellipse cx="23" cy="30" rx="16" ry="7" transform="rotate(120 23 30)" />
                    </g>
                    <circle cx="23" cy="30" r="3.2" fill="#adfff4" />
                  </svg>
                </div>
                <div className="absolute right-0 top-2.5 h-[60px] w-[46px] rotate-[12deg] overflow-hidden rounded-lg shadow-lg ring-1 ring-white/15">
                  <svg viewBox="0 0 46 60" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
                    <rect width="46" height="60" fill="#04140d" />
                    <path
                      d="M13 27 L10 13 L20 21 Q23 20 26 21 L36 13 L33 27 Q38 35 32 43 Q23 50 14 43 Q8 35 13 27 Z"
                      fill="#0a2a20" stroke="#27ffa1" strokeWidth="1.1" strokeOpacity="0.65"
                    />
                    <path d="M13 24 L12 16 L18 21 Z" fill="#27ffa1" fillOpacity="0.3" />
                    <path d="M33 24 L34 16 L28 21 Z" fill="#27ffa1" fillOpacity="0.3" />
                    <g fill="#5ffda1">
                      <path d="M16 31 Q19 27 22 31 Q19 34 16 31 Z" />
                      <path d="M24 31 Q27 27 30 31 Q27 34 24 31 Z" />
                    </g>
                  </svg>
                </div>
                <div className="absolute left-1/2 top-0 h-[66px] w-[48px] -translate-x-1/2 overflow-hidden rounded-lg shadow-xl ring-1 ring-white/25">
                  <svg viewBox="0 0 48 66" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
                    <rect width="48" height="66" fill="#123a6b" />
                    <circle cx="32" cy="20" r="9" fill="#eafff6" />
                    <circle cx="28" cy="17" r="9" fill="#123a6b" />
                    <g fill="#adfff4">
                      <circle cx="12" cy="14" r="1" />
                      <circle cx="18" cy="30" r="0.8" />
                      <circle cx="10" cy="40" r="1.1" />
                      <circle cx="38" cy="44" r="0.9" />
                    </g>
                  </svg>
                </div>
              </div>
            }
          />
          <StepCard
            n={4}
            title="Time's up = we lock it."
            desc="After your session ends, the app locks for 2 hours so you can actually get to work."
            preview={
              <div className="relative inline-flex origin-center scale-[0.8] flex-col items-center gap-1.5 px-6 py-5">
                <svg viewBox="0 0 96 96" className="pointer-events-none absolute -inset-1 -z-0 h-[calc(100%+8px)] w-[calc(100%+8px)]" preserveAspectRatio="none" aria-hidden="true">
                  <path
                    d="M48 6 L82 20 L82 46 C82 66 66 80 48 88 C30 80 14 66 14 46 L14 20 Z"
                    fill="#27ffa1" fillOpacity="0.2" stroke="#27ffa1" strokeOpacity="0.45" strokeWidth="1.4"
                  />
                </svg>
                <svg viewBox="0 0 24 24" className="relative size-8 text-[#27ffa1]" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="4" y="10" width="16" height="11" rx="3" fill="currentColor" fillOpacity="0.15" />
                  <path d="M7.5 10V7a4.5 4.5 0 0 1 9 0v3" />
                  <circle cx="12" cy="14.8" r="1.7" fill="currentColor" stroke="none" />
                  <path d="M12 16.3V18.4" />
                </svg>
                <span className="relative text-[11px] font-bold tracking-wide text-[#adfff4]" style={{ fontFamily: '"Geist:ExtraBold", sans-serif' }}>2:00:00</span>
              </div>
            }
          />
        </ol>

        <button
          onClick={onBegin}
          className="btn-pressable group mt-1 mb-4 inline-flex items-center gap-3 self-center text-[22px] font-bold tracking-tight text-[#27ffa1] transition-all hover:text-[#5ffda1] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#27ffa1] focus-visible:ring-offset-4 focus-visible:ring-offset-[#020c07] rounded-full"
        >
          Let&apos;s Begin
          <span className="flex size-10 items-center justify-center rounded-full border border-[#27ffa1]/60 transition-all group-hover:bg-[#27ffa1] group-hover:text-[#04120b] group-hover:translate-x-1">
            <ArrowRight className="size-5 transition-transform group-hover:translate-x-0.5" />
          </span>
        </button>
      </div>
    </div>
  );
}
