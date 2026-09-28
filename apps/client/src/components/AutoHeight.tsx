import { useEffect, useRef, useState, type ReactNode } from "react";

interface AutoHeightProps {
  children: ReactNode;
  className?: string;
  duration?: number;
}

/**
 * AutoHeight smoothly animates its container height whenever the children's
 * dimensions change (e.g. card swap, "Read more" toggle, interaction reveal).
 */
export default function AutoHeight({
  children,
  className = "",
  duration = 340,
}: AutoHeightProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | undefined>(undefined);

  useEffect(() => {
    if (!contentRef.current) return;
    const el = contentRef.current;

    const measure = () => {
      if (contentRef.current) {
        setHeight(contentRef.current.offsetHeight);
      }
    };

    measure();

    const observer = new ResizeObserver(() => {
      measure();
    });
    observer.observe(el);

    return () => observer.disconnect();
  }, [children]);

  return (
    <div
      className={`card-auto-height overflow-hidden ${className}`}
      style={{
        height: height !== undefined ? `${height}px` : "auto",
        transitionDuration: `${duration}ms`,
      }}
    >
      <div ref={contentRef} className="w-full">
        {children}
      </div>
    </div>
  );
}
