import { useEffect } from "react";
import { ThemeProvider } from "./lib/theme";
import { AppFrame } from "./components/ui";
import ScreenNavigator from "./components/ScreenNavigator";
import { ClarifySheet, EndEarlySheet, ReportSheet } from "./components/Sheets";
import { useApp } from "./store";

export default function App() {
  const { ready, screen, toast, boot, setScreen } = useApp();

  useEffect(() => { void boot(); }, [boot]);

  const sceneTone = screen === "welcome" || screen === "how" || screen === "locked" ? "scene" : "light";

  return (
    <ThemeProvider>
      <AppFrame tone={sceneTone}>
        {!ready ? (
          <div className="grid h-full place-items-center bg-[#04120b] text-[#27ffa1]">…</div>
        ) : (
          <ScreenNavigator screen={screen} onSetScreen={setScreen} />
        )}

        <ClarifySheet />
        <ReportSheet />
        <EndEarlySheet />

        {toast && (
          <div className="absolute bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-full bg-[#0b2719] px-4 py-2 text-[13px] font-medium text-[#adfff4] shadow-lg ring-1 ring-[#27ffa1]/30">
            {toast}
          </div>
        )}
      </AppFrame>
    </ThemeProvider>
  );
}
