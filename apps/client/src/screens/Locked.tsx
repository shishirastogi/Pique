import { useEffect } from "react";
import Countdown from "../components/Countdown";
import { useApp } from "../stores/app";

export default function Locked() {
  const { lock, setModal, pollLock } = useApp();

  useEffect(() => {
    const t = window.setInterval(() => void pollLock(), 30_000);
    return () => clearInterval(t);
  }, [pollLock]);

  if (!lock?.locked || !lock.lock_until) return null;
  const until = new Date(lock.lock_until);

  return (
    <div className="screen center locked">
      <div className="stack">
        <div className="lock-icon" aria-hidden>🔒</div>
        <h1 className="big-title">LOCKED</h1>
        <p className="lead">You're warmed up. Now go do the work.</p>

        <div className="lock-timer">
          <Countdown until={lock.lock_until} onExpire={() => void pollLock()} />
        </div>
        <p className="hint">Unlocks at {until.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</p>

        <button className="btn ghost" onClick={() => setModal("emergencyUnlock")}>
          Emergency unlock
        </button>
      </div>
    </div>
  );
}
