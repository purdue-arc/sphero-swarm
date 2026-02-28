import styles from './App.module.css'
import { Sidebar } from "../components/Sidebar/sidebar"
import { Runner } from "../components/Runner/runner"
import { Controls } from "../components/Controls/Controls"
import { Config } from "../components/Config/config"
import { Simulation } from "../components/Simulation/simulation"
import { useState, useEffect } from 'react'
import type { SpheroConstants, SpheroStatus } from '../types/swarm_types'

declare global {
  interface Window {
    electronAPI: {
      appRenderComplete: () => Promise<any>;
      signalAppReady(): unknown
      getConstants: any;
      startSpheroSpotter: () => Promise<any>;
      stopSpheroSpotter: () => Promise<any>;
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

  useEffect(() => {
    async function loadConstants() {
      try {
        const data = await window.electronAPI.getConstants();
        setConstants(data);
        setAppReady(true);
        // Signal to splash that render is complete, showing the button
        window.electronAPI.appRenderComplete();
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

  // Calculate connected robots for sidebar
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
          <Runner constants={constants} spheros={spheros} setSpheros={setSpheros} />
        )}

        {currentView === "configuration" && (
          <Config constants={constants} onUpdate={setConstants} />
        )}

        {currentView === "controls" && (
          <Controls constants={constants} spheros={spheros} setSpheros={setSpheros} />
        )}

        {currentView === "simulation" && (
          <Simulation constants={constants} spheros={spheros} setSpheros={setSpheros} />
        )}

        {/* Placeholder views for other sections */}
        {currentView === "perception" && (
          <div style={{ padding: '2rem', color: '#ffffff' }}>
            <h1>Perception Module</h1>
            <p>Detailed perception controls and monitoring coming soon...</p>
          </div>
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