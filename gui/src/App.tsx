import styles from './App.module.css'
import { Sidebar } from "../components/Sidebar/sidebar"
import { Runner } from "../components/Runner/runner"
import { Controls } from "../components/Controls/Controls"
import { Config } from "../components/Config/config"
import { Simulation } from "../components/Simulation/simulation"
import { Perception } from "../components/Perception/perception"

import { useState, useEffect } from 'react'
import type { SpheroConstants, SpheroStatus, PerceptionConfig, SimulationSnapshot } from '../types/swarm_types'

declare global {
  interface Window {
    electronAPI: {
      appRenderComplete: () => Promise<any>;
      signalAppReady(): unknown
      getConstants: any;
      startSpheroSpotter: (config?: PerceptionConfig) => Promise<any>;
      stopSpheroSpotter: () => Promise<any>;
      startControls: () => Promise<any>;
      stopControls: () => Promise<any>;
      refreshControls: () => Promise<any>;
      quitApp: () => Promise<any>;
      saveConstants: (form: any) => Promise<any>;
    };
  }
}

function App() {
  const [currentView, setCurrentView] = useState<string>("dashboard")
  const [constants, setConstants] = useState<SpheroConstants | null>(null);
  const [spheros, setSpheros] = useState<SpheroStatus[]>([])
  const [authReady, setAppReady] = useState(false);
  const [algorithmRunning, setAlgorithmRunning] = useState(false);
  const [perceptionStatus, setPerceptionStatus] = useState<"stopped" | "starting" | "started">("stopped");
  const [perceptionConfig, setPerceptionConfig] = useState<PerceptionConfig>({
    inputSource: "oakd",
    videoPath: "",
    model: "./models/bestv3.pt",
    conf: 0.25,
    imgsz: 640,
    grid: false,
    locked: false,
    latency: false,
  });
  const [latestSimulationSnapshot, setLatestSimulationSnapshot] = useState<SimulationSnapshot | null>(null);
  const [simulationSpeed, setSimulationSpeed] = useState(6);
  const [useControls, setUseControls] = useState(false);
  const [useAlgorithmColors, setUseAlgorithmColors] = useState(true);

  useEffect(() => {
    async function loadConstants() {
      try {
        const data = await window.electronAPI.getConstants();
        setConstants(data);
        setAppReady(true);
        // Signal to splash that render is complete, showing the button
        window.electronAPI.appRenderComplete();
        window.electronAPI.startControls()
      } catch (err) {
        console.error("Failed to load constants:", err);
        setAppReady(true);
        window.electronAPI.appRenderComplete();
      }
    }

    loadConstants();
  }, []);

  useEffect(() => {
    if (!constants)
      return;

    setSpheros(
      constants.SPHERO_TAGS.map((tag, i) => ({
        id: tag,
        connection: "not-attempted",
        actualPosition: [0, 0],
        expectedPosition: constants.INITIAL_POSITIONS[i],
      }))
    );
  }, [constants])

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let dead = false;

    const connect = () => {
      if (dead) return;
      ws = new WebSocket("ws://localhost:6769");

      ws.onmessage = (event) => {
        try {
          const payload: SimulationSnapshot = JSON.parse(event.data);
          setLatestSimulationSnapshot(payload);
        } catch {
          // ignore malformed payloads
        }
      };

      ws.onclose = () => {
        if (!dead) {
          reconnectTimer = setTimeout(connect, 1000);
        }
      };

      ws.onerror = () => ws?.close();
    };

    connect();

    return () => {
      dead = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  if (constants == null || !authReady) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: 'linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%)',
        color: '#ffffff',
        fontSize: '1.5rem',
        fontWeight: 600
      }}>
        Loading system...
      </div>
    )
  }

  const connectedRobots = spheros.filter(s => s.connection === "connected").length;

  return (
    <div className={styles.mainBody}>
      <Sidebar
        currentView={currentView}
        setCurrentView={setCurrentView}
        connectedRobots={connectedRobots}
      />
      <div className={styles.viewer}>
        {currentView === "dashboard" && (
          <Runner
            constants={constants}
            spheros={spheros}
            perceptionStatus={perceptionStatus}
            setPerceptionStatus={setPerceptionStatus}
            latestSimulationSnapshot={latestSimulationSnapshot}
            onSimulationSnapshot={setLatestSimulationSnapshot}
            speed={simulationSpeed}
            onSpeedChange={setSimulationSpeed}
            useControls={useControls}
            onUseControlsChange={setUseControls}
            useAlgorithmColors={useAlgorithmColors}
            onUseAlgorithmColorsChange={setUseAlgorithmColors}
          />
        )}

        {currentView === "configuration" && (
          <Config constants={constants} onUpdate={setConstants} algorithmRunning={algorithmRunning} />
        )}

        {currentView === "controls" && (
          <Controls constants={constants} spheros={spheros} setSpheros={setSpheros} algorithmRunning={algorithmRunning} />
        )}

        {currentView === "simulation" && (
          <Simulation
            constants={constants}
            onRunningChange={setAlgorithmRunning}
            latestSnapshot={latestSimulationSnapshot}
            onSnapshot={setLatestSimulationSnapshot}
            speed={simulationSpeed}
            onSpeedChange={setSimulationSpeed}
            useControls={useControls}
            onUseControlsChange={setUseControls}
            useAlgorithmColors={useAlgorithmColors}
            onUseAlgorithmColorsChange={setUseAlgorithmColors}
          />
        )}

        {/* Placeholder views for other sections */}
        {currentView === "perception" && (
          <Perception
            spotterStatus={perceptionStatus}
            setSpotterStatus={setPerceptionStatus}
            config={perceptionConfig}
            setConfig={setPerceptionConfig}
          />
        )}

        {currentView === "algorithms" && (
          <div style={{ padding: '2rem', color: '#ffffff' }}>
            <h1>Algorithms Module</h1>
            <p>Algorithm configuration and testing coming soon...</p>
          </div>
        )}

        {currentView === "about" && (
          <div style={{ padding: '2rem', color: '#ffffff' }}>
            <h1>About Us</h1>
            <p>Team information and project details coming soon...</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default App