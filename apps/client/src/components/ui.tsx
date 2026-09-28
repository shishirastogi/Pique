import type { ButtonHTMLAttributes, ReactNode } from "react";
import { ArrowRight } from "./icons";

/* Shared mobile app-frame: a fixed phone aspect ratio, centered on wide viewports */
export function AppFrame({ children, tone = "light" }: { children: ReactNode; tone?: "light" | "dark" | "scene" }) {
  const shell = tone === "light" ? "bg-[color:var(--background)]" : "bg-[#04120b]";
  return (
    <div className={`flex min-h-[100dvh] w-full justify-center transition-colors duration-500 md:items-center md:p-6 ${shell}`}>
      <div className="relative h-[100dvh] w-full max-w-[430px] overflow-hidden bg-[color:var(--background)] md:h-auto md:aspect-[9/16] md:max-h-[860px] md:rounded-[44px] md:shadow-[0_50px_130px_-30px_rgba(0,60,35,0.55)] md:ring-1 md:ring-black/10 dark:md:ring-white/10">
        <div className="h-full w-full overflow-hidden">{children}</div>
      </div>
    </div>
  );
}

/* Rounded pill button used across primary actions */
export function PillButton({
  children,
  variant = "solid",
  withArrow,
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "solid" | "ghost" | "mint";
  withArrow?: boolean;
}) {
  const styles: Record<string, string> = {
    solid:
      "bg-[color:var(--brand)] text-white hover:brightness-110 dark:text-[#04120b]",
    mint: "bg-[#27ffa1] text-[#04120b] hover:bg-[#5ffda1]",
    ghost:
      "bg-transparent text-[color:var(--brand)] hover:bg-[color:var(--surface-2)]",
  };
  return (
    <button
      {...rest}
      className={`group inline-flex items-center justify-center gap-2 rounded-full px-7 py-3.5 text-[17px] font-semibold tracking-tight transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-transparent active:scale-[0.98] ${styles[variant]} ${className}`}
    >
      {children}
      {withArrow && (
        <ArrowRight className="size-[18px] transition-transform duration-200 group-hover:translate-x-0.5" />
      )}
    </button>
  );
}

/* Selectable chip / segmented option */
export function Chip({
  active,
  children,
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      {...rest}
      className={`rounded-full border px-4 py-2 text-sm font-medium transition-all duration-200 active:scale-[0.97] ${
        active
          ? "border-transparent bg-[#27ffa1] text-[#04120b] shadow-[0_4px_16px_-4px_rgba(39,255,161,0.6)]"
          : "border-[color:var(--border-strong)] bg-[color:var(--surface)] text-[color:var(--foreground)] hover:border-[color:var(--accent)]"
      } ${className}`}
    >
      {children}
    </button>
  );
}

/* Accessible toggle switch */
export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label?: string;
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative flex h-7 w-[52px] shrink-0 items-center rounded-full p-0.5 transition-colors duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-transparent ${
        checked ? "bg-[color:var(--accent)]" : "bg-[color:var(--border-strong)]"
      }`}
    >
      <span
        className={`block size-6 rounded-full bg-white shadow-md transition-transform duration-300 ease-out ${
          checked ? "translate-x-[24px]" : "translate-x-0"
        }`}
      />
    </button>
  );
}
