import { useEffect, useRef, useState } from "react";
import { ArrowRight, ChevronLeft, Flag } from "../components/icons";
import ThemeToggle from "../components/ThemeToggle";
import CardView from "../components/CardView";
import AutoHeight from "../components/AutoHeight";
import { PillButton, Chip } from "../components/ui";
import { useApp } from "../store";

export default function Session() {
  const {
    session, items, cursor, nextCard, prevCard, setSheet, setEngagement,
    markShown, completeSession, pauseSession, resumeSession, progress,
  } = useApp();
  const card = items[cursor];
  const isLast = cursor === items.length - 1;
  const endsAt = session ? new Date(session.ends_at).getTime() : Date.now();
  const [left, setLeft] = useState(Math.max(0, endsAt - Date.now()));
  const [isPaused, setIsPaused] = useState(false);
  const leftRef = useRef(left);
  leftRef.current = left;

  const [cardDirection, setCardDirection] = useState<"next" | "prev">("next");
  const prevCursorRef = useRef(cursor);
  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(null);

  useEffect(() => {
    setLeft(Math.max(0, endsAt - Date.now()));
  }, [endsAt]);

  useEffect(() => {
    if (cursor > prevCursorRef.current) {
      setCardDirection("next");
    } else if (cursor < prevCursorRef.current) {
      setCardDirection("prev");
    }
    prevCursorRef.current = cursor;
  }, [cursor]);

  useEffect(() => { if (card) markShown(cursor); }, [cursor, card, markShown]);

  // Pause countdown when screen locks or app minimizes; resume seamlessly when user returns
  useEffect(() => {
    const handleHide = () => {
      setIsPaused(true);
      const remSec = Math.max(1, Math.round(leftRef.current / 1000));
      pauseSession(remSec);
    };

    const handleShow = () => {
      setIsPaused(false);
      void resumeSession();
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        handleHide();
      } else if (document.visibilityState === "visible") {
        handleShow();
      }
    };

    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("pagehide", handleHide);
    window.addEventListener("pageshow", handleShow);
    window.addEventListener("blur", handleHide);
    window.addEventListener("focus", handleShow);

    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("pagehide", handleHide);
      window.removeEventListener("pageshow", handleShow);
      window.removeEventListener("blur", handleHide);
      window.removeEventListener("focus", handleShow);
    };
  }, [pauseSession, resumeSession]);

  useEffect(() => {
    if (isPaused) return;

    const t = window.setInterval(() => {
      const rem = Math.max(0, endsAt - Date.now());
      setLeft(rem);
      if (rem === 0) void completeSession(null);  // hard stop: countdown owns the session
    }, 1000);
    return () => clearInterval(t);
  }, [endsAt, isPaused, completeSession]);

  const total = Math.ceil(left / 1000);
  const mm = String(Math.floor(total / 60)).padStart(2, "0");
  const ss = String(total % 60).padStart(2, "0");
  const urgent = left <= 30_000;

  if (!session) return null;

  const handleNext = () => {
    setCardDirection("next");
    nextCard();
  };

  const handlePrev = () => {
    if (cursor > 0) {
      setCardDirection("prev");
      prevCard();
    }
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0];
    touchStartRef.current = { x: t.clientX, y: t.clientY, time: Date.now() };
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!touchStartRef.current) return;
    const t = e.changedTouches[0];
    const dx = t.clientX - touchStartRef.current.x;
    const dy = t.clientY - touchStartRef.current.y;
    const dt = Date.now() - touchStartRef.current.time;
    touchStartRef.current = null;

    // Detect horizontal swipe (at least 35px, more horizontal than vertical, under 600ms)
    if (Math.abs(dx) > 35 && Math.abs(dx) > Math.abs(dy) * 1.2 && dt < 600) {
      if (dx < 0 && !isLast) {
        handleNext();
      } else if (dx > 0 && cursor > 0) {
        handlePrev();
      }
    }
  };

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" && !isLast) handleNext();
      else if (e.key === "ArrowLeft" && cursor > 0) handlePrev();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  return (
    <div className="flex h-full w-full flex-col overflow-y-auto scene-scroll overscroll-contain bg-[color:var(--background)] px-6 pb-8 pt-10 text-[color:var(--foreground)] transition-colors duration-500">
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

      {/* content card with auto-adjusting height, swipe gestures and sliding animations */}
      <div
        className="my-auto py-2 w-full flex flex-col min-h-fit touch-pan-y"
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        {card ? (
          <AutoHeight duration={360} className="w-full">
            <div
              key={card.content_id ?? cursor}
              className={`w-full ${
                cardDirection === "next" ? "anim-card-in-next" : "anim-card-in-prev"
              }`}
            >
              <CardView
                card={card}
                initialEngagement={progress[cursor]?.engagement}
                onEngage={(e) => setEngagement(cursor, e)}
              />
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

      {/* footer: report + prev/skip/next */}
      <div className="mt-4 flex items-center justify-between">
        <button
          onClick={() => setSheet("report")}
          className="btn-pressable inline-flex items-center gap-1.5 text-[13px] font-medium text-[color:var(--muted-foreground)] underline underline-offset-4 transition-colors hover:text-[color:var(--accent)]"
        >
          <Flag className="size-3.5" /> Report
        </button>
        <div className="flex items-center gap-2">
          {cursor > 0 && (
            <Chip onClick={handlePrev} className="btn-pressable text-xs px-3 py-1.5">
              Prev
            </Chip>
          )}
          {!isLast && (
            <Chip onClick={handleNext} className="btn-pressable text-xs px-3 py-1.5">
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
