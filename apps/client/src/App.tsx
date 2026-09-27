import { useEffect } from "react";
import { api, ApiError, getToken } from "./lib/api";
import { deviceFp } from "./lib/device";
import { useApp } from "./stores/app";
import Home from "./screens/Home";
import Generating from "./screens/Generating";
import Player from "./screens/Player";
import Complete from "./screens/Complete";
import Locked from "./screens/Locked";
import { ClarifyModal, EmergencyUnlockModal, EndEarlyModal, ReportModal } from "./components/Modals";

export default function App() {
  const { ready, screen, toast, modal, init } = useApp();

  useEffect(() => {
    (async () => {
      try {
        if (!getToken()) await api.auth(deviceFp());
        await init();
      } catch (e) {
        useApp.setState({
          ready: true,
          error: e instanceof ApiError ? e.message : "Startup failed",
        });
      }
    })();
  }, [init]);

  if (!ready) return <div className="boot">…</div>;

  return (
    <div className="phone">
      {screen === "home" && <Home />}
      {screen === "generating" && <Generating />}
      {screen === "player" && <Player />}
      {screen === "complete" && <Complete />}
      {screen === "locked" && <Locked />}

      {modal === "clarify" && <ClarifyModal />}
      <ReportModal />
      {modal === "endEarly" && <EndEarlyModal />}
      {modal === "emergencyUnlock" && <EmergencyUnlockModal />}

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
