// Card renderer in the Pique design language (docs/05 §6), driven by real
// ContentCard payloads. Long bodies clamp with Read more (user rule).
import { useEffect, useState } from "react";
import type { ContentCard } from "../types";
import { Chip } from "./ui";

const LONG_BODY = 240;

function clampBody(text: string): string {
  if (text.length <= LONG_BODY) return text;
  const cut = text.slice(0, LONG_BODY);
  const stop = Math.max(cut.lastIndexOf(". "), cut.lastIndexOf("! "), cut.lastIndexOf("? "));
  const at = stop > LONG_BODY * 0.4 ? stop + 1 : (cut.lastIndexOf(" ") > 0 ? cut.lastIndexOf(" ") : LONG_BODY);
  return text.slice(0, at) + " …";
}

const TYPE_LABEL: Record<string, string> = {
  meme: "meme", interesting_fact: "did you know", quote: "quote",
  visual_explanation: "see it first", analogy: "analogy",
  poll: "poll", question: "question", mini_story: "story", trivia: "trivia",
  historical_context: "context", diagram: "diagram", reaction_gif: "gif",
  micro_lesson: "micro lesson", challenge: "challenge",
  first_work_action: "your first step", book_excerpt: "from the archives",
};

export default function CardView({
  card, onEngage, initialEngagement,
}: {
  card: ContentCard;
  onEngage: (e: Record<string, unknown>) => void;
  initialEngagement?: Record<string, unknown>;
}) {
  const [revealed, setRevealed] = useState(() => Boolean(initialEngagement?.reveal || initialEngagement?.answer));
  const [hintShown, setHintShown] = useState(() => Boolean(initialEngagement?.hint));
  const [voted, setVoted] = useState<number | null>(() => typeof initialEngagement?.poll_choice === "number" ? (initialEngagement.poll_choice as number) : null);
  const [choice, setChoice] = useState<boolean | null>(() => initialEngagement?.challenge ? (initialEngagement.challenge === "accepted") : null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setRevealed(Boolean(initialEngagement?.reveal || initialEngagement?.answer));
    setHintShown(Boolean(initialEngagement?.hint));
    setVoted(typeof initialEngagement?.poll_choice === "number" ? (initialEngagement.poll_choice as number) : null);
    setChoice(initialEngagement?.challenge ? (initialEngagement.challenge === "accepted") : null);
    setExpanded(false);
  }, [card.content_id, initialEngagement]);

  const it = card.interaction;
  const isLong = card.body.length > LONG_BODY;
  const img = card.media?.url;

  return (
    <div
      className="flex w-full flex-col rounded-[32px] border border-[color:var(--border)] bg-[color:var(--surface)] p-5 shadow-[0_16px_40px_-16px_rgba(0,30,15,0.09)] dark:shadow-[0_20px_50px_-20px_rgba(0,0,0,0.5)] transition-colors duration-300"
      key={card.content_id}
    >
      {/* visual panel */}
      <div
        className={`relative w-full overflow-hidden rounded-[22px] border border-[color:var(--border)] bg-[color:var(--panel)] anim-rise anim-d1 flex flex-col items-center justify-center transition-all duration-300 ${
          img ? "min-h-[120px]" : "h-[104px] p-3"
        }`}
      >
        {img ? (
          <img
            src={img}
            alt={card.title ?? card.type}
            className="w-full h-auto max-h-[500px] object-contain block transition-transform duration-500 ease-out hover:scale-[1.01]"
            referrerPolicy="no-referrer"
            loading="eager"
          />
        ) : (
          <div className="flex flex-col items-center gap-1 text-center">
            <span
              className="text-[34px] font-extrabold text-[color:var(--accent)]/80"
              style={{ fontFamily: '"Geist:ExtraBold", sans-serif' }}
            >
              {card.type === "quote"
                ? "“”"
                : card.type === "question"
                ? "?"
                : card.type === "poll"
                ? "▮▯▯"
                : card.type === "challenge"
                ? "⏱"
                : card.type === "analogy"
                ? "⇄"
                : "✳"}
            </span>
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)]">
              {TYPE_LABEL[card.type] ?? card.type}
            </span>
          </div>
        )}
        <span className="absolute left-3.5 top-3.5 rounded-full bg-black/60 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-white backdrop-blur-md shadow-sm z-10">
          {TYPE_LABEL[card.type] ?? card.type}
        </span>
        {card.attribution?.required && card.attribution.text && (
          <div className="w-full bg-black/70 px-3 py-1.5 text-[9.5px] leading-tight text-white/90 backdrop-blur-sm z-10">
            {card.attribution.text}
          </div>
        )}
      </div>

      {/* copy */}
      <div className="mt-4">
        {card.title && (
          <h3 className="anim-rise anim-d2 text-[17.5px] font-bold leading-snug text-[color:var(--foreground)]">
            {card.title}
          </h3>
        )}
        <p className="anim-rise anim-d3 mt-1.5 whitespace-pre-line text-[14px] leading-relaxed text-[color:var(--muted-foreground)]">
          {expanded ? card.body : clampBody(card.body)}
        </p>
        {isLong && (
          <button
            onClick={() => setExpanded((e) => !e)}
            className="btn-pressable mt-1.5 text-[12.5px] font-semibold text-[color:var(--accent)] underline underline-offset-4"
          >
            {expanded ? "Show less" : "Read more"}
          </button>
        )}
      </div>

      {/* interactions */}
      {it?.kind === "reveal" && (
        <div className="anim-rise anim-d4 mt-3">
          {revealed ? (
            <div className="rounded-2xl bg-[color:var(--surface-2)] px-4 py-3 text-[13.5px] font-medium text-[color:var(--brand)]">
              <span className="font-bold text-[color:var(--accent)]">Reveal: </span>
              {it.reveal}
            </div>
          ) : (
            <Chip
              className="btn-pressable"
              active
              onClick={() => {
                setRevealed(true);
                onEngage({ reveal: true });
              }}
            >
              Reveal
            </Chip>
          )}
        </div>
      )}

      {it?.kind === "question" && (
        <div className="anim-rise anim-d4 mt-3 flex flex-col gap-2">
          {hintShown && it.hint && (
            <div className="rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface-2)] px-4 py-2.5 text-[13px] text-[color:var(--muted-foreground)]">
              <span className="font-semibold text-[color:var(--accent)]">Hint: </span>
              {it.hint}
            </div>
          )}
          {revealed ? (
            <div className="rounded-2xl bg-[color:var(--surface-2)] px-4 py-3 text-[13.5px] font-medium text-[color:var(--brand)]">
              <span className="font-bold text-[color:var(--foreground)]">Answer: </span>
              {it.answer || it.hint}
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {it.hint && !hintShown && (
                <Chip
                  className="btn-pressable"
                  onClick={() => {
                    setHintShown(true);
                    onEngage({ hint: true });
                  }}
                >
                  Show hint
                </Chip>
              )}
              <Chip
                className="btn-pressable"
                active
                onClick={() => {
                  setRevealed(true);
                  onEngage({ reveal: true });
                }}
              >
                Show answer
              </Chip>
            </div>
          )}
        </div>
      )}

      {it?.kind === "poll" && it.options && (
        <div className="anim-rise anim-d4 mt-3 flex flex-col gap-2">
          {voted === null ? (
            it.options.map((o, i) => (
              <button
                key={i}
                onClick={() => { setVoted(i); onEngage({ poll_choice: i }); }}
                className="btn-pressable w-full rounded-2xl border border-[color:var(--border-strong)] bg-[color:var(--surface)] px-4 py-2.5 text-left text-[13.5px] font-medium transition-colors hover:border-[color:var(--accent)] hover:bg-[color:var(--surface-2)]"
              >
                {o}
              </button>
            ))
          ) : (
            <p className="rounded-2xl bg-[color:var(--surface-2)] px-4 py-3 text-[13.5px] font-medium text-[color:var(--brand)]">
              Noted — “{it.options[voted]}”.
            </p>
          )}
        </div>
      )}

      {it?.kind === "challenge" && (
        <div className="anim-rise anim-d4 mt-3 flex gap-2">
          {choice === null ? (
            <>
              <Chip className="btn-pressable" active onClick={() => { setChoice(true); onEngage({ challenge: "accepted" }); }}>
                I&apos;ll try it
              </Chip>
              <Chip className="btn-pressable" onClick={() => { setChoice(false); onEngage({ challenge: "declined" }); }}>
                Not now
              </Chip>
            </>
          ) : (
            <p className="rounded-2xl bg-[color:var(--surface-2)] px-4 py-3 text-[13.5px] font-medium text-[color:var(--brand)]">
              {choice ? "Go. 90 seconds." : "It's waiting when you are."}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
