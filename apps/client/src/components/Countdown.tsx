import { useEffect, useState } from "react";

/** Always-visible countdown (anti-distraction affordance, docs/05 §13). */
export default function Countdown({ until, onExpire }: { until: string; onExpire?: () => void }) {
  const target = new Date(until).getTime();
  const [left, setLeft] = useState(() => Math.max(0, target - Date.now()));

  useEffect(() => {
    const t = window.setInterval(() => {
      const rem = Math.max(0, target - Date.now());
      setLeft(rem);
      if (rem === 0 && onExpire) { clearInterval(t); onExpire(); }
    }, 1000);
    return () => clearInterval(t);
  }, [target, onExpire]);

  const total = Math.ceil(left / 1000);
  const mm = String(Math.floor(total / 60)).padStart(2, "0");
  const ss = String(total % 60).padStart(2, "0");
  const cls = left <= 30_000 ? "countdown red" : left <= 120_000 ? "countdown amber" : "countdown";
  return <span className={cls}>{mm}:{ss}</span>;
}
