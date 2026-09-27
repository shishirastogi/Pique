export default function ProgressDots({ total, current }: { total: number; current: number }) {
  return (
    <div className="dots" aria-label={`Card ${current + 1} of ${total}`}>
      {Array.from({ length: total }, (_, i) => (
        <span key={i} className={i < current ? "dot done" : i === current ? "dot now" : "dot"} />
      ))}
      <span className="dots-count">{current + 1} / {total}</span>
    </div>
  );
}
