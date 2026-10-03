import { useState } from "react";
import { Chip, Toggle } from "../components/ui";
import ThemeToggle from "../components/ThemeToggle";
import { ArrowRight, ChevronLeft, Minus, Plus } from "../components/icons";
import { useApp, hasOnboarded } from "../store";
import type { Duration } from "../types";

const CATEGORIES = ["Work", "Study", "Project", "Other"];
const TIMES: { label: string; m: Duration }[] = [
  { label: "5 mins", m: 5 }, { label: "10 mins", m: 10 },
  { label: "15 mins", m: 15 }, { label: "20 mins", m: 20 },
];

function formatLockDuration(minutes: number): string {
  const hrs = minutes / 60;
  if (minutes % 60 === 0) {
    return `${hrs} ${hrs === 1 ? "hr" : "hrs"}`;
  }
  return `${hrs.toFixed(1)} hrs`;
}

// category chip nudges the parser toward the right goal when text is terse
const CATEGORY_PREFIX: Record<string, string> = {
  Work: "For work: ",
  Study: "I need to study ",
  Project: "For my project: ",
  Other: "",
};

export default function FillDetails({ onBack }: { onBack: () => void }) {
  const { startFlow, busy, error } = useApp();
  const [topic, setTopic] = useState("");
  const [category, setCategory] = useState("Study");
  const [time, setTime] = useState<Duration>(10);
  const [lockMinutes, setLockMinutes] = useState<number>(120);

  const submit = () => {
    const raw = topic.trim();
    if (!raw || busy) return;
    const prefixed = /^i (need|have|want|must|should)/i.test(raw)
      ? raw
      : CATEGORY_PREFIX[category] + raw.charAt(0).toLowerCase() + raw.slice(1);
    void startFlow(prefixed, time, lockMinutes);
  };

  return (
    <div className="flex h-full w-full flex-col overflow-y-auto scene-scroll bg-[color:var(--background)] px-7 pb-9 pt-14 text-[color:var(--foreground)] transition-colors duration-500">
      {/* header */}
      <div className="flex items-center justify-between">
        {!hasOnboarded() ? (
          <button
            onClick={onBack}
            aria-label="Go back"
            className="btn-pressable -ml-2 flex size-9 items-center justify-center rounded-full text-[color:var(--muted-foreground)] transition-colors hover:bg-[color:var(--surface-2)]"
          >
            <ChevronLeft className="size-5 transition-transform group-hover:-translate-x-0.5" />
          </button>
        ) : (
          <span
            className="text-[20px] font-extrabold tracking-tight text-[color:var(--brand)]"
            style={{ fontFamily: '"Geist:ExtraBold", sans-serif' }}
          >
            Pique
          </span>
        )}
        <ThemeToggle />
      </div>

      <h1
        className="mt-6 leading-[1.02] text-[color:var(--brand)]"
        style={{ fontFamily: '"Geist:ExtraBold", sans-serif', fontWeight: 800, fontSize: 34, letterSpacing: "-0.8px" }}
      >
        Let&apos;s Fill
        <br />
        the Details
      </h1>

      {/* topic input */}
      <label className="mt-8 block">
        <textarea
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          rows={3}
          placeholder="What do you need to work on?"
          className="w-full resize-none rounded-3xl border border-[color:var(--border)] bg-[color:var(--surface)] px-5 py-4 text-[15px] leading-relaxed text-[color:var(--foreground)] placeholder:text-[color:var(--muted-foreground)] transition-colors focus-visible:border-[color:var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring)]"
        />
      </label>

      <div className="mt-6 flex flex-wrap gap-3.5">
        {CATEGORIES.map((c) => (
          <Chip key={c} active={category === c} onClick={() => setCategory(c)}>
            {c}
          </Chip>
        ))}
      </div>

      {/* time & custom lockout selector */}
      <div className="mt-8 rounded-3xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 sm:p-5">
        <div className="flex items-center justify-between gap-3 sm:gap-4">
          <div className="flex-1">
            <span className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--muted-foreground)]">
              Warm-up
            </span>
            <div className="grid grid-cols-2 gap-2">
              {TIMES.map((t) => (
                <Chip
                  key={t.m}
                  active={time === t.m}
                  onClick={() => setTime(t.m)}
                  className="w-full justify-center px-2 py-2 text-[13px]"
                >
                  {t.label}
                </Chip>
              ))}
            </div>
          </div>

          <div className="h-20 w-px bg-[color:var(--border)]" />

          {/* custom lockout period option (minimum 1 hour) */}
          <div className="flex min-w-[104px] flex-col items-center justify-center text-center">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--muted-foreground)]">
              Lockout
            </span>
            <div
              className="mt-1 text-[color:var(--accent)]"
              style={{ fontFamily: '"Geist:ExtraBold", sans-serif', fontWeight: 800, fontSize: 24, letterSpacing: "-0.5px" }}
            >
              {formatLockDuration(lockMinutes)}
            </div>
            <div className="mt-2 flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setLockMinutes((m) => Math.max(60, m - 30))}
                disabled={lockMinutes <= 60}
                aria-label="Decrease lockout period (minimum 1 hour)"
                title="Decrease lockout period (minimum 1 hour)"
                className="btn-pressable flex size-7 items-center justify-center rounded-full border border-[color:var(--border)] bg-[color:var(--surface-2)] text-[color:var(--foreground)] transition-all hover:bg-[color:var(--surface-3)] active:scale-95 disabled:cursor-not-allowed disabled:opacity-30"
              >
                <Minus className="size-3.5 stroke-[2.5]" />
              </button>
              <button
                type="button"
                onClick={() => setLockMinutes((m) => Math.min(480, m + 30))}
                disabled={lockMinutes >= 480}
                aria-label="Increase lockout period"
                title="Increase lockout period"
                className="btn-pressable flex size-7 items-center justify-center rounded-full border border-[color:var(--border)] bg-[color:var(--surface-2)] text-[color:var(--foreground)] transition-all hover:bg-[color:var(--surface-3)] active:scale-95 disabled:cursor-not-allowed disabled:opacity-30"
              >
                <Plus className="size-3.5 stroke-[2.5]" />
              </button>
            </div>
            <span className="mt-1.5 text-[10px] font-medium text-[color:var(--muted-foreground)]">
              Min 1 hr
            </span>
          </div>
        </div>
      </div>

      {/* lock other apps — native shell feature (docs/02 decision), visual placeholder */}
      <div className="mt-8 flex items-center justify-between opacity-60">
        <p className="text-[15px] font-medium">
          Lock Other Apps?{" "}
          <span className="text-[color:var(--accent)] underline decoration-[color:var(--accent)]/40 underline-offset-4">
            Soon — mobile builds
          </span>
        </p>
        <Toggle checked={false} onChange={() => undefined} label="Lock other apps (coming soon)" />
      </div>

      {error && (
        <p className="mt-4 rounded-2xl bg-red-500/10 px-4 py-3 text-[13px] font-medium text-red-400">
          {error}
        </p>
      )}

      <div className="mt-auto flex justify-center pt-10">
        <button
          onClick={submit}
          disabled={!topic.trim() || busy}
          className="btn-pressable group inline-flex items-center gap-3 text-[22px] font-bold tracking-tight text-[color:var(--accent)] transition-all hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring)] focus-visible:ring-offset-4 focus-visible:ring-offset-[color:var(--background)] rounded-full disabled:opacity-40"
        >
          {busy ? "Warming up…" : "Start"}
          <span className="flex size-9 items-center justify-center rounded-full border border-[color:var(--accent)]/50 transition-all group-hover:bg-[color:var(--accent)] group-hover:text-[color:var(--background)] group-hover:translate-x-1">
            <ArrowRight className="size-[18px] transition-transform group-hover:translate-x-0.5" />
          </span>
        </button>
      </div>
    </div>
  );
}
