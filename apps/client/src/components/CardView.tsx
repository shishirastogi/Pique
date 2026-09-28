// Card renderer in the Pique design language (docs/05 §6), driven by real
// ContentCard payloads. Long bodies clamp with Read more (user rule).
import { useState } from "react";
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
  card, onEngage,
}: { card: ContentCard; onEngage: (e: Record<string, unknown>) => void }) {
  const [revealed, setRevealed] = useState(false);
  const [voted, setVoted] = useState<number | null>(null);
  const [choice, setChoice] = useState<boolean | null>(null);
  const [expanded, setExpanded] = useState(false);
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
        className={`relative w-full overflow-hidden rounded-[22px] border border-[color:var(--border)] bg-[color:var(--panel)] anim-rise anim-d1 shrink-0 ${
          img ? "aspect-[16/10] max-h-[210px]" : "h-[104px] flex flex-col items-center justify-center p-3"
        }`}
      >
        {img ? (
          <img
            src={img}
            alt={card.title ?? card.type}
            className="absolute inset-0 h-full w-full object-cover transition-transform duration-700 ease-out hover:scale-105"
            referrerPolicy="no-referrer"
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
        <span className="absolute left-3.5 top-3.5 rounded-full bg-black/50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-white backdrop-blur-md">
          {TYPE_LABEL[card.type] ?? card.type}
        </span>
        {card.attribution?.required && card.attribution.text && (
          <span className="absolute inset-x-0 bottom-0 bg-black/60 px-3 py-1.5 text-[9.5px] leading-tight text-white/90 backdrop-blur-sm">
            {card.attribution.text}
          </span>
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
            <p className="rounded-2xl bg-[color:var(--surface-2)] px-4 py-3 text-[13.5px] font-medium text-[color:var(--brand)]">
              {it.reveal}
            </p>
          ) : (
            <Chip className="btn-pressable" onClick={() => { setRevealed(true); onEngage({ reveal: true }); }}>Reveal</Chip>
          )}
        </div>
      )}

      {it?.kind === "question" && (
        <div className="anim-rise anim-d4 mt-3 flex flex-wrap gap-2">
          {it.hint && !revealed && (
            <Chip className="btn-pressable" onClick={() => onEngage({ hint: true })}>Show hint</Chip>
          )}
          {!revealed ? (
            <Chip className="btn-pressable" onClick={() => setRevealed(true)}>Show answer</Chip>
          ) : (
            <p className="w-full rounded-2xl bg-[color:var(--surface-2)] px-4 py-3 text-[13.5px] font-medium text-[color:var(--brand)]">
              {it.hint}{it.answer ? ` ${it.answer}` : ""}
            </p>
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
