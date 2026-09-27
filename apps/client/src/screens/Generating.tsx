import { useEffect, useState } from "react";
import { useApp } from "../stores/app";

const STEPS = [
  "Understanding your task",
  "Finding interesting material",
  "Personalizing to you",
  "Planning your minutes",
  "Final check",
];

export default function Generating() {
  const { duration, cancelGeneration } = useApp();
  const [step, setStep] = useState(0);

  useEffect(() => {
    const t = window.setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 900);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="screen center">
      <div className="stack">
        <h2 className="gen-title">Building your {duration}-minute warm-up…</h2>
        <ul className="gen-steps">
          {STEPS.map((s, i) => (
            <li key={s} className={i < step ? "done" : i === step ? "now" : ""}>
              {i < step ? "✓ " : ""}{s}
            </li>
          ))}
        </ul>
        <button className="btn ghost" onClick={cancelGeneration}>Cancel</button>
      </div>
    </div>
  );
}
