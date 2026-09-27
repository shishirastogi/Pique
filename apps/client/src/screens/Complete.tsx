import { useApp } from "../stores/app";

export default function Complete() {
  const { session, progress, completeSession, abandoned, items } = useApp();
  const skipped = Object.values(progress).filter((p) => p.skipped).length;
  const seen = Object.values(progress).filter((p) => p.shownAt).length || items.length;

  return (
    <div className="screen center">
      <div className="stack">
        <h1 className="big-title">{abandoned ? "Warm-up ended early" : "WARM-UP COMPLETE"}</h1>
        <p className="lead">You have enough context. Now go do the work.</p>

        {session && (
          <div className="chips summary">
            <span className="chip">{session.task.topic}</span>
            <span className="chip">{session.duration_minutes} min</span>
            <span className="chip">{seen} cards</span>
            {skipped > 0 && <span className="chip">{skipped} skipped</span>}
          </div>
        )}

        <p className="hint">The app locks for 2 hours once you continue. That's the deal.</p>

        <button className="btn primary big" onClick={() => void completeSession(true)}>
          I'm starting now →
        </button>
        <button className="btn ghost" onClick={() => void completeSession(false)}>
          Not yet
        </button>
      </div>
    </div>
  );
}
