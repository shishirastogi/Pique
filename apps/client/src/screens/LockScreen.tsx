import { useEffect, useState } from "react";
import { Clock, Lock } from "../components/icons";
import ThemeToggle from "../components/ThemeToggle";
import SceneBackground from "../components/SceneBackground";
import { useApp } from "../store";

export default function LockScreen() {
  const { lock, pollLock, setSheet } = useApp();
  const until = lock?.lock_until ? new Date(lock.lock_until).getTime() : Date.now();
  const [left, setLeft] = useState(Math.max(0, until - Date.now()));

  useEffect(() => {
    const poll = window.setInterval(() => void pollLock(), 30_000);   // server authority (docs/04 §5)
    const tick = window.setInterval(() => setLeft(Math.max(0, until - Date.now())), 1000);

    const handleVisible = () => {
      if (document.visibilityState === "visible") {
        setLeft(Math.max(0, until - Date.now()));
        void pollLock();
      }
    };
    document.addEventListener("visibilitychange", handleVisible);
    window.addEventListener("focus", handleVisible);

    return () => {
      clearInterval(poll);
      clearInterval(tick);
      document.removeEventListener("visibilitychange", handleVisible);
      window.removeEventListener("focus", handleVisible);
    };
  }, [until, pollLock]);

  const total = Math.floor(left / 1000);
  const hh = String(Math.floor(total / 3600)).padStart(2, "0");
  const mm = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
  const ss = String(total % 60).padStart(2, "0");

  const lockMinutes = lock?.minutes ?? (lock?.remaining_seconds ? Math.round(lock.remaining_seconds / 60) : 120);
  const lockHours = lockMinutes / 60;
  const lockDurationText =
    lockMinutes % 60 === 0
      ? `${lockHours} ${lockHours === 1 ? "hour" : "hours"}`
      : `${lockHours.toFixed(1)} hours`;

  return (
    <main className="relative flex h-full w-full flex-col overflow-y-auto scene-scroll bg-[#04120b] px-7 pb-8 pt-11 text-white">
      <SceneBackground className="opacity-30 mix-blend-screen" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_31%,rgba(39,255,161,0.24),transparent_30%),linear-gradient(180deg,rgba(4,18,11,0.2),rgba(4,18,11,0.9)_72%)]" />

      <div className="relative z-10 flex items-center justify-between">
        <span className="text-[15px] font-semibold tracking-[-0.03em] text-[#eafff4]">Pique</span>
        <ThemeToggle />
      </div>

      <div className="relative z-10 flex flex-1 flex-col items-center justify-center pb-10 text-center">
        <div className="relative mb-9 grid size-36 place-items-center rounded-full border border-[#86feca]/25 bg-[#0c2a1b]/80 shadow-[0_0_0_12px_rgba(39,255,161,0.05),0_24px_65px_rgba(0,0,0,0.4)] backdrop-blur-sm">
          <div className="grid size-24 place-items-center rounded-[30px] border border-[#86feca]/20 bg-[#27ffa1] text-[#04321d] shadow-[inset_0_1px_0_rgba(255,255,255,0.6),0_10px_30px_rgba(39,255,161,0.22)]">
            <Lock className="size-11 stroke-[2.25]" />
          </div>
          <span className="absolute -right-1 bottom-2 grid size-10 place-items-center rounded-full border-4 border-[#082014] bg-[#eafff4] text-[#005f36] shadow-lg">
            <Clock className="size-4 stroke-[2.5]" />
          </span>
        </div>

        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#86feca]">Session complete</p>
        <h1 className="max-w-[300px] text-[37px] font-extrabold leading-[0.98] tracking-[-0.065em] text-[#eafff4]">
          Nice work. Now go make it count.
        </h1>
        <p className="mt-5 max-w-[282px] text-[15px] leading-[1.55] text-[#b4d9c3]">
          Pique is locked for the next {lockDurationText}, so your attention stays where you put it.
        </p>

        <div className="mt-8 flex items-center gap-3 rounded-full border border-[#86feca]/20 bg-[#0b2719]/80 px-5 py-3 text-left backdrop-blur-sm">
          <span className="grid size-8 place-items-center rounded-full bg-[#27ffa1] text-[#04321d]">
            <Clock className="size-4 stroke-[2.5]" />
          </span>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.13em] text-[#8fbaa4]">Unlocks in</p>
            <p className="mt-0.5 text-[17px] font-bold leading-none tabular-nums tracking-[-0.04em] text-white">
              {hh}:{mm}:{ss}
            </p>
          </div>
        </div>
      </div>

      <div className="relative z-10 flex flex-col items-center gap-3 text-center">
        <p className="text-[11px] text-[#6f9c85]">Countdown hits zero → back to the welcome screen.</p>
        <button
          onClick={() => setSheet("emergency")}
          className="btn-pressable text-[12px] font-medium text-[#547864] underline decoration-[#547864]/45 underline-offset-4 transition-colors hover:text-[#eafff4]"
        >
          Emergency unlock
        </button>
      </div>
    </main>
  );
}
