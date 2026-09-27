import { useState } from "react";
import { useApp } from "../stores/app";
import type { Duration } from "../types";

const EXAMPLES = [
  "I need to study thermodynamics for my exam tomorrow, I'm weak at it",
  "I need to design a climate-change awareness poster",
  "I need to understand JavaScript closures",
];
const DURATIONS: Duration[] = [5, 10, 15, 20];

export default function Home() {
  const [text, setText] = useState("");
  const { duration, setDuration, submitPrompt, error } = useApp();

  return (
    <div className="screen">
      <header className="home-head">
        <h1 className="wordmark">FocusWarmup</h1>
        <p className="tagline">Get curious about it first. Then go do it.</p>
      </header>

      <main className="composer">
        <label className="composer-label" htmlFor="mission">What do you need to work on?</label>
        <textarea
          id="mission" value={text} maxLength={500} rows={3}
          placeholder={EXAMPLES[0]}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && text.trim()) void submitPrompt(text.trim()); }}
        />
        <div className="composer-meta">
          <span>{text.length}/500</span>
        </div>

        <div className="chips">
          {EXAMPLES.map((ex) => (
            <button key={ex} className="chip" onClick={() => setText(ex)}>{ex.split(",")[0]}…</button>
          ))}
        </div>

        <div className="duration-row" role="radiogroup" aria-label="Warm-up length">
          {DURATIONS.map((d) => (
            <button key={d} className={d === duration ? "chip sel" : "chip"}
              onClick={() => setDuration(d)}>{d} min</button>
          ))}
        </div>
        <p className="hint">App locks for 2 hours after the session — that's the point.</p>

        {error && <p className="error">{error}</p>}

        <button className="btn primary big" disabled={!text.trim()}
          onClick={() => void submitPrompt(text.trim())}>
          Start Warm-up
        </button>
      </main>
    </div>
  );
}
