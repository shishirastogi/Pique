// One renderer per content type (docs/05 §6). Mock content has no media yet;
// media-aware rendering lands with real providers (08-phase).
import { useState } from "react";
import type { ContentCard } from "../types";

const TYPE_LABEL: Record<string, string> = {
  meme: "meme", interesting_fact: "did you know", quote: "quote",
  visual_explanation: "see it first", analogy: "analogy", joke: "joke",
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
  const it = card.interaction;

  return (
    <article className={`card card-${card.type}`}>
      <div className="card-badge">{TYPE_LABEL[card.type] ?? card.type}</div>
      {card.title && <h2 className="card-title">{card.title}</h2>}

      {card.media?.kind === "image" && card.media.url && (
        <figure className="card-figure">
          <img className="card-media" src={card.media.url} alt={card.title ?? card.type} loading="lazy" />
          {card.attribution?.required && card.attribution.text && (
            <figcaption className="card-attr">
              {card.attribution.source_url
                ? <a href={card.attribution.source_url} target="_blank" rel="noreferrer">{card.attribution.text}</a>
                : card.attribution.text}
            </figcaption>
          )}
        </figure>
      )}

      <p className="card-body">{card.body}</p>

      {it?.kind === "reveal" && (
        revealed
          ? <p className="card-reveal">{it.reveal}</p>
          : <button className="btn ghost" onClick={() => { setRevealed(true); onEngage({ reveal: true }); }}>Reveal</button>
      )}

      {it?.kind === "question" && (
        <div className="stack">
          {it.hint && <button className="btn ghost" onClick={() => onEngage({ hint: true })}>Show hint</button>}
          {revealed
            ? <p className="card-reveal">{it.hint ?? ""}{it.answer ? ` ${it.answer}` : ""}</p>
            : <button className="btn ghost" onClick={() => setRevealed(true)}>Show answer</button>}
        </div>
      )}

      {it?.kind === "poll" && it.options && (
        <div className="stack">
          {it.question && <p className="card-sub">{it.question}</p>}
          {voted === null ? it.options.map((o, i) => (
            <button key={i} className="btn option"
              onClick={() => { setVoted(i); onEngage({ poll_choice: i }); }}>{o}</button>
          )) : <p className="card-reveal">Noted — {it.options[voted]}. That feeling is why we're here.</p>}
        </div>
      )}

      {it?.kind === "challenge" && (
        choice === null
          ? <div className="row">
              <button className="btn option" onClick={() => { setChoice(true); onEngage({ challenge: "accepted" }); }}>I'll try it</button>
              <button className="btn ghost" onClick={() => { setChoice(false); onEngage({ challenge: "declined" }); }}>Not now</button>
            </div>
          : <p className="card-reveal">{choice ? "Timer's yours — go." : "No problem, it's waiting when you are."}</p>
      )}
    </article>
  );
}
