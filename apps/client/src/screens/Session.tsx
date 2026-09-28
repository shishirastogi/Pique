import { useEffect, useRef, useState } from "react";
import { ArrowRight, ChevronLeft, Flag } from "../components/icons";
import ThemeToggle from "../components/ThemeToggle";
import CardView from "../components/CardView";
import AutoHeight from "../components/AutoHeight";
import { PillButton, Chip } from "../components/ui";
import { useApp } from "../store";

export default function Session() {
  const {
    session, items, cursor, nextCard, setSheet, setEngagement,
    markShown, completeSession,
  } = useApp();
  const card = items[cursor];
  const isLast = cursor === items.length - 1;
  const endsAt = session ? new Date(session.ends_at).getTime() : Date.now();
  const [left, setLeft] = useState(Math.max(0, endsAt - Date.now()));
  const [cardDirection, setCardDirection] = useState<"next" | "prev">("next");
  const prevCursorRef = useRef(cursor);

  useEffect(() => {
    if (cursor > prevCursorRef.current) {
      setCardDirection("next");
    } else if (cursor < prevCursorRef.current) {
      setCardDirection("prev");
    }
    prevCursorRef.current = cursor;
  }, [cursor]);

  useEffect(() => { if (card) markShown(cursor); }, [cursor, card, markShown]);

  useEffect(() => {
    const t = window.setInterval(() => {
      const rem = Math.max(0, endsAt - Date.now());
      setLeft(rem);
      if (rem === 0) void completeSession(null);  // hard stop: countdown owns the session
    }, 1000);
    return () => clearInterval(t);
  }, [endsAt, completeSession]);

  const total = Math.ceil(left / 1000);
  const mm = String(Math.floor(total / 60)).padStart(2, "0");
  const ss = String(total % 60).padStart(2, "0");
  const urgent = left <= 30_000;

  if (!session) return null;

  const handleNext = () => {
    setCardDirection("next");
    nextCard();
  };

  return (
    <div className="flex h-full w-full flex-col overflow-y-auto scene-scroll bg-[color:var(--background)] px-7 pb-8 pt-14 text-[color:var(--foreground)] transition-colors duration-500">
      {/* header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setSheet("endEarly")}
          aria-label="End early"
          className="btn-pressable -ml-2 flex size-9 items-center justify-center rounded-full text-[color:var(--muted-foreground)] transition-colors hover:bg-[color:var(--surface-2)]"
        >
          <ChevronLeft className="size-5 transition-transform group-hover:-translate-x-0.5" />
        </button>
        <ThemeToggle />
      </div>

      {/* topic + time left */}
      <div className="mt-3 flex items-start justify-between">
        <h1
          className="leading-[1.02] text-[color:var(--brand)]"
          style={{ fontFamily: '"Geist:ExtraBold", sans-serif', fontWeight: 800, fontSize: 30, letterSpacing: "-0.8px" }}
        >
          {session.task.topic}
        </h1>
        <div className="text-right">
          <div className="text-[11px] font-semibold uppercase tracking-widest text-[color:var(--muted-foreground)]">
            Time Left
          </div>
          <div
            className={`tabular-nums ${urgent ? "text-red-400" : "text-[color:var(--accent)]"}`}
            style={{ fontFamily: '"Geist:ExtraBold", sans-serif', fontWeight: 800, fontSize: 22, letterSpacing: "0.5px" }}
          >
            {mm}:{ss}
          </div>
        </div>
      </div>

      {/* progress + end early */}
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {[0, 1, 2].map((i) => {
            const bucket = cursor / Math.max(items.length - 1, 1);
            const active = Math.round(bucket * 2) === i;
            return (
              <span
                key={i}
                className={`size-3.5 rounded-full transition-colors duration-300 ${
                  active ? "bg-[color:var(--accent)]" : "bg-[color:var(--border-strong)]"
                }`}
              />
            );
          })}
          <span className="ml-2 text-[12px] font-semibold text-[color:var(--muted-foreground)]">
            {cursor + 1} / {items.length}
          </span>
        </div>
        <button
          onClick={() => setSheet("endEarly")}
          className="btn-pressable group inline-flex items-center gap-2 text-[14px] font-semibold text-[color:var(--foreground)] transition-colors hover:text-[color:var(--accent)]"
        >
          End Early
          <span className="flex size-6 items-center justify-center rounded-full border border-current transition-all group-hover:bg-[color:var(--accent)] group-hover:text-[color:var(--background)]">
            <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
          </span>
        </button>
      </div>

      {/* content card with auto-adjusting height and sliding animations */}
      <div className="mt-4 flex-1 flex flex-col justify-center min-h-0">
        {card ? (
          <AutoHeight duration={360} className="w-full">
            <div
              key={card.content_id ?? cursor}
              className={`w-full ${
                cardDirection === "next" ? "anim-card-in-next" : "anim-card-in-prev"
              }`}
            >
              <CardView card={card} onEngage={(e) => setEngagement(cursor, e)} />
            </div>
          </AutoHeight>
        ) : (
          <div className="flex min-h-[200px] w-full items-center justify-center rounded-[32px] border border-[color:var(--border)] bg-[color:var(--panel)] p-8">
            <span className="text-[15px] font-medium text-[color:var(--muted-foreground)]">
              Preparing your warm-up…
            </span>
          </div>
        )}
      </div>

      {/* footer: report + skip/next */}
      <div className="mt-4 flex items-center justify-between">
        <button
          onClick={() => setSheet("report")}
          className="btn-pressable inline-flex items-center gap-1.5 text-[13px] font-medium text-[color:var(--muted-foreground)] underline underline-offset-4 transition-colors hover:text-[color:var(--accent)]"
        >
          <Flag className="size-3.5" /> Report
        </button>
        <div className="flex items-center gap-3">
          {!isLast && (
            <Chip onClick={handleNext} className="btn-pressable">
              Skip
            </Chip>
          )}
          {isLast ? (
            <PillButton
              variant="mint"
              onClick={() => void completeSession(null)}
              className="btn-pressable"
            >
              Finish warm-up ✓
            </PillButton>
          ) : (
            <PillButton
              variant="solid"
              withArrow
              onClick={handleNext}
              className="btn-pressable"
            >
              Next
            </PillButton>
          )}
        </div>
      </div>
    </div>
  );
}
