import SceneBackground from "../components/SceneBackground";
import { ArrowRight } from "../components/icons";

export default function Welcome({ onStart }: { onStart: () => void }) {
  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden bg-[#04120b] text-white">
      <SceneBackground />

      {/* legibility scrims */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-56 bg-gradient-to-b from-[#04120b]/75 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-[62%] bg-gradient-to-t from-[#020c07] via-[#020c07]/70 to-transparent" />

      <div className="relative flex flex-1 flex-col justify-between px-9 pb-12 pt-16">
        {/* top subtext — preserved Geist Medium 21px */}
        <p
          className="w-[300px] leading-snug"
          style={{ fontFamily: '"Geist:Medium", sans-serif', fontWeight: 500, fontSize: 21 }}
        >
          <span className="text-[#4fb98a]">Turn whatever you need to do into something you want to </span>
          <span className="text-[#27ffa1]">explore.</span>
        </p>

        <div>
          {/* hero — preserved Geist ExtraBold 55px / 50px / -0.55px */}
          <h1
            className="mb-8"
            style={{
              fontFamily: '"Geist:ExtraBold", sans-serif',
              fontWeight: 800,
              fontSize: 55,
              lineHeight: "50px",
              letterSpacing: "-0.55px",
            }}
          >
            <span className="text-white">Get curious. </span>
            <span
              className="bg-clip-text text-transparent"
              style={{
                backgroundImage:
                  "radial-gradient(ellipse at center, #5ffda1 0%, #5ffda1 56.731%, #86feca 78.365%, #adfff4 100%)",
                WebkitBackgroundClip: "text",
              }}
            >
              and get to work.
            </span>
          </h1>

          <button
            onClick={onStart}
            className="btn-pressable group inline-flex items-center gap-3 text-[19px] font-semibold tracking-tight text-[#27ffa1] transition-all hover:text-[#5ffda1] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#27ffa1] focus-visible:ring-offset-4 focus-visible:ring-offset-[#020c07] rounded-full"
          >
            Get Started
            <span className="flex size-9 items-center justify-center rounded-full border border-[#27ffa1]/60 transition-all group-hover:bg-[#27ffa1] group-hover:text-[#04120b] group-hover:translate-x-1">
              <ArrowRight className="size-[18px] transition-transform group-hover:translate-x-0.5" />
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}
