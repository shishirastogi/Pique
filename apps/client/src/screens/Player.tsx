import { useCallback, useEffect } from "react";
import CardView from "../cards/CardView";
import Countdown from "../components/Countdown";
import ProgressDots from "../components/ProgressDots";
import { useApp } from "../stores/app";

export default function Player() {
  const {
    session, items, cursor, nextCard, setModal, setEngagement,
    markShown, completeSession, hardTimeout,
  } = useApp();

  const card = items[cursor];
  const isLast = cursor === items.length - 1;

  useEffect(() => { if (card) markShown(cursor); }, [cursor, card, markShown]);

  const skip = useCallback(() => {
    const p = useApp.getState().progress[cursor];
    useApp.setState({
      progress: { ...useApp.getState().progress,
        [cursor]: { ...(p ?? { shownAt: Date.now(), dwellMs: 0 }), skipped: true } },
    });
    useApp.getState().setToast("Noted — fewer like this next time.");
    if (isLast) void completeSession(null); else nextCard();
  }, [cursor, isLast, nextCard, completeSession]);

  if (!session || !card) return null;
  const topic = session.task.topic;

  return (
    <div className="screen player">
      <header className="player-head">
        <div>
          <div className="player-task">{topic}</div>
          <div className="player-goal">{session.task.goal.replaceAll("_", " ")}</div>
        </div>
        <Countdown until={session.ends_at} onExpire={() => void hardTimeout()} />
      </header>

      <ProgressDots total={items.length} current={cursor} />
      <div className="phase-tag">{card.phase}</div>

      <div className="card-wrap" key={card.content_id}>
        <CardView card={card} onEngage={(e) => setEngagement(cursor, e)} />
      </div>

      <footer className="player-foot">
        <button className="btn ghost" onClick={() => setModal("report")}>⚑ Report</button>
        {isLast ? (
          <button className="btn ghost" onClick={skip}>Skip</button>
        ) : (
          <button className="btn ghost" onClick={skip}>⟲ Skip</button>
        )}
        {isLast ? (
          <button className="btn primary" onClick={() => void completeSession(null)}>
            Finish warm-up ✓
          </button>
        ) : (
          <button className="btn primary" onClick={nextCard}>Next →</button>
        )}
      </footer>
      <button className="link-quiet" onClick={() => setModal("endEarly")}>End early</button>
    </div>
  );
}
