// Bottom-sheet overlays in the Pique design language: clarify, report,
// end-early confirm, emergency unlock (docs/05 §§3,7,9,12).
import { useState } from "react";
import { useApp } from "../store";
import { Chip, PillButton } from "./ui";

function Sheet({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div
      className="absolute inset-0 z-40 flex items-end bg-black/55 backdrop-blur-[2px]"
      onClick={onClose}
    >
      <div
        className="w-full rounded-t-[28px] border-t border-[color:var(--border)] bg-[color:var(--background)] p-6 pb-9 text-[color:var(--foreground)]"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

export function ClarifySheet() {
  const { sheet, clarifyQuestion, clarifyOptions, answerClarify, skipClarify, task } = useApp();
  if (sheet !== "clarify") return null;
  return (
    <Sheet onClose={() => void skipClarify()}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
        One quick thing — {task?.topic}
      </p>
      <h3 className="mt-2 text-[19px] font-bold">{clarifyQuestion}</h3>
      <div className="mt-4 flex flex-wrap gap-2.5">
        {clarifyOptions?.map((o: string) => (
          <Chip key={o} className="capitalize" onClick={() => void answerClarify(o)}>{o}</Chip>
        ))}
      </div>
      <button
        onClick={() => void skipClarify()}
        className="mt-4 text-[12.5px] font-medium text-[color:var(--muted-foreground)] underline underline-offset-4"
      >
        Skip — just start
      </button>
    </Sheet>
  );
}

const REASONS: [string, string][] = [
  ["inappropriate", "Inappropriate"], ["wrong", "Wrong or misleading"],
  ["copyright", "Copyright concern"], ["off_topic", "Off-topic"], ["other", "Other"],
];

export function ReportSheet() {
  const { sheet, setSheet, reportCurrent } = useApp();
  const [reason, setReason] = useState(REASONS[0][0]);
  const [comment, setComment] = useState("");
  if (sheet !== "report") return null;
  return (
    <Sheet onClose={() => setSheet("none")}>
      <h3 className="text-[19px] font-bold">Report this card</h3>
      <div className="mt-4 flex flex-col gap-2.5">
        {REASONS.map(([k, label]) => (
          <label key={k} className="flex items-center gap-3 text-[14px] font-medium">
            <input
              type="radio" name="report-reason" checked={reason === k}
              onChange={() => setReason(k)} className="accent-[#00a85f] size-4"
            />
            {label}
          </label>
        ))}
        <textarea
          rows={2} placeholder="Optional comment" value={comment}
          onChange={(e) => setComment(e.target.value)}
          className="mt-1 w-full resize-none rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] px-4 py-3 text-[13.5px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring)]"
        />
      </div>
      <div className="mt-5 flex justify-end gap-3">
        <PillButton variant="ghost" onClick={() => setSheet("none")}>Cancel</PillButton>
        <PillButton variant="solid" onClick={() => void reportCurrent(reason, comment || undefined)}>
          Submit report
        </PillButton>
      </div>
    </Sheet>
  );
}

export function EndEarlySheet() {
  const { sheet, setSheet, endEarly } = useApp();
  if (sheet !== "endEarly") return null;
  return (
    <Sheet onClose={() => setSheet("none")}>
      <h3 className="text-[19px] font-bold">End warm-up early?</h3>
      <p className="mt-2 text-[13.5px] leading-relaxed text-[color:var(--muted-foreground)]">
        Your warm-up ends and the 2-hour lock still starts — that part is the point.
      </p>
      <div className="mt-5 flex justify-end gap-3">
        <PillButton variant="ghost" onClick={() => setSheet("none")}>Keep going</PillButton>
        <PillButton variant="solid" onClick={() => void endEarly()}>End warm-up</PillButton>
      </div>
    </Sheet>
  );
}
