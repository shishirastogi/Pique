// Modals: clarify (07 §4.2), report (05 §7), end-early confirm, emergency unlock (05 §9).
import { useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../stores/app";

function Shell({ children, onClose }: { children: React.ReactNode; onClose?: () => void }) {
  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>{children}</div>
    </div>
  );
}

export function ClarifyModal() {
  const { clarifyQuestion, clarifyOptions, answerClarify, skipClarify, task } = useApp();
  return (
    <Shell>
      <p className="modal-sub">{task?.topic} · quick calibration</p>
      <h3>{clarifyQuestion}</h3>
      <div className="stack">
        {clarifyOptions?.map((o) => (
          <button key={o} className="btn option" onClick={() => answerClarify(o)}>{o}</button>
        ))}
      </div>
      <button className="link-quiet" onClick={skipClarify}>Skip</button>
    </Shell>
  );
}

export function ReportModal() {
  const { modal, setModal, items, cursor, session, setToast } = useApp();
  const [reason, setReason] = useState("inappropriate");
  const [comment, setComment] = useState("");
  if (modal !== "report") return null;
  const card = items[cursor];
  const REASONS: [string, string][] = [
    ["inappropriate", "Inappropriate"], ["wrong", "Wrong or misleading"],
    ["copyright", "Copyright concern"], ["off_topic", "Off-topic"], ["other", "Other"],
  ];
  return (
    <Shell onClose={() => setModal("none")}>
      <h3>Report this card</h3>
      <div className="stack">
        {REASONS.map(([k, label]) => (
          <label key={k} className="radio">
            <input type="radio" checked={reason === k} onChange={() => setReason(k)} /> {label}
          </label>
        ))}
        <textarea rows={2} placeholder="Optional comment" value={comment}
          onChange={(e) => setComment(e.target.value)} />
      </div>
      <div className="row">
        <button className="btn ghost" onClick={() => setModal("none")}>Cancel</button>
        <button className="btn danger" onClick={() => {
          if (!card) return;
          void api.reportContent({ content_id: card.content_id, session_id: session?.session_id, reason, comment })
            .catch(() => undefined);
          setModal("none");
          setToast("Reported. Thanks — this feeds moderation.");
        }}>Submit report</button>
      </div>
    </Shell>
  );
}

export function EndEarlyModal() {
  const { endEarly, setModal } = useApp();
  return (
    <Shell onClose={() => setModal("none")}>
      <h3>End warm-up early?</h3>
      <p>Your warm-up will end and the 2-hour lock still starts.</p>
      <div className="row">
        <button className="btn ghost" onClick={() => setModal("none")}>Keep going</button>
        <button className="btn danger" onClick={() => void endEarly()}>End warm-up</button>
      </div>
    </Shell>
  );
}

export function EmergencyUnlockModal() {
  const { emergencyUnlock, setModal } = useApp();
  const [text, setText] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const ok = text === "I NEED TO STOP";
  return (
    <Shell onClose={() => setModal("none")}>
      <h3>Emergency unlock</h3>
      <p>This breaks your commitment and is logged. Type <code>I NEED TO STOP</code> to unlock.</p>
      <input value={text} onChange={(e) => setText(e.target.value)} placeholder="I NEED TO STOP" />
      {err && <p className="error">{err}</p>}
      <div className="row">
        <button className="btn ghost" onClick={() => setModal("none")}>Cancel</button>
        <button className="btn danger" disabled={!ok} onClick={() =>
          emergencyUnlock(text).catch((e) => setErr(e.message))}>Unlock</button>
      </div>
    </Shell>
  );
}
