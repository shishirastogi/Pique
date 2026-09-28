import { Moon, Sun } from "./icons";
import { useTheme } from "../lib/theme";

/** Consistent light/dark switch used across the light-mode screens. */
export default function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";
  return (
    <button
      onClick={toggle}
      role="switch"
      aria-checked={isDark}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="relative flex h-8 w-[68px] items-center rounded-full bg-[color:var(--accent)] p-1 transition-colors active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--background)]"
    >
      <span
        className={`flex size-6 items-center justify-center rounded-full bg-white text-[color:var(--accent)] shadow-md transition-transform duration-300 ease-out ${
          isDark ? "translate-x-9" : "translate-x-0"
        }`}
      >
        {isDark ? <Moon className="size-3.5" /> : <Sun className="size-3.5" />}
      </span>
    </button>
  );
}
