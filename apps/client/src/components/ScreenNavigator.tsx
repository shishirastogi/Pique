import { useEffect, useRef, useState, type ReactNode } from "react";
import { hasOnboarded, setOnboarded, type Screen } from "../store";
import Welcome from "../screens/Welcome";
import HowItWorks from "../screens/HowItWorks";
import FillDetails from "../screens/FillDetails";
import Session from "../screens/Session";
import LockScreen from "../screens/LockScreen";

const SCREEN_ORDER: Record<Screen, number> = {
  welcome: 0,
  how: 1,
  details: 2,
  session: 3,
  locked: 4,
};

interface ScreenNavigatorProps {
  screen: Screen;
  onSetScreen: (screen: Screen) => void;
}

export default function ScreenNavigator({
  screen,
  onSetScreen,
}: ScreenNavigatorProps) {
  const [activeScreen, setActiveScreen] = useState<Screen>(screen);
  const [outgoingScreen, setOutgoingScreen] = useState<Screen | null>(null);
  const [direction, setDirection] = useState<"fwd" | "back">("fwd");
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (screen === activeScreen) return;

    const isForward =
      SCREEN_ORDER[screen] >= (SCREEN_ORDER[activeScreen] ?? 0) &&
      !(activeScreen === "locked" && screen === "welcome");

    const newDirection = isForward ? "fwd" : "back";

    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    setOutgoingScreen(activeScreen);
    setActiveScreen(screen);
    setDirection(newDirection);

    timerRef.current = window.setTimeout(() => {
      setOutgoingScreen(null);
      timerRef.current = null;
    }, 440);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [screen, activeScreen]);

  const renderScreen = (s: Screen): ReactNode => {
    switch (s) {
      case "welcome":
        return <Welcome onStart={() => onSetScreen("how")} />;
      case "how":
        return (
          <HowItWorks
            onBegin={() => {
              setOnboarded();
              onSetScreen("details");
            }}
          />
        );
      case "details":
        return (
          <FillDetails
            onBack={() => {
              if (!hasOnboarded()) onSetScreen("how");
            }}
          />
        );
      case "session":
        return <Session />;
      case "locked":
        return <LockScreen />;
    }
  };

  const isTransitioning = outgoingScreen !== null;

  return (
    <div className="relative h-full w-full overflow-hidden">
      {/* Outgoing view during transition */}
      {outgoingScreen && (
        <div
          key={`out-${outgoingScreen}`}
          className={`absolute inset-0 h-full w-full overflow-hidden pointer-events-none will-change-transform ${
            direction === "fwd"
              ? "z-10 anim-screen-out-fwd"
              : "z-20 anim-screen-out-back anim-screen-shadow"
          }`}
        >
          {renderScreen(outgoingScreen)}
        </div>
      )}

      {/* Incoming / Active view */}
      <div
        key={`active-${activeScreen}`}
        className={`h-full w-full ${
          isTransitioning
            ? `absolute inset-0 overflow-hidden will-change-transform ${
                direction === "fwd"
                  ? "z-20 anim-screen-in-fwd anim-screen-shadow"
                  : "z-10 anim-screen-in-back"
              }`
            : "relative"
        }`}
      >
        {renderScreen(activeScreen)}
      </div>
    </div>
  );
}
