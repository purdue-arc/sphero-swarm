import styles from './App.module.css'
import { Sidebar } from "../components/Sidebar/sidebar"
import { Runner } from "../components/Runner/runner"
import { Config } from "../components/Config/config"
import { useState, useEffect } from 'react'
import type { SpheroConstants, SpheroStatus } from '../types/swarm_types'

declare global {
  interface Window {
    electronAPI: {
      getConstants: any;
      startSpheroSpotter: () => Promise<any>;
      stopSpheroSpotter: () => Promise<any>;
    };
  }
}

function App() {
  const [currentView, setCurrentView] = useState<string>("dashboard")
  const [constants, setConstants] = useState<SpheroConstants | null>(null);
  const [spheros, setSpheros] = useState<SpheroStatus[]>([])

  useEffect(() => {
    // Load constants from Python via Electron
    async function loadConstants() {
      try {
        const data = await window.electronAPI.getConstants();
        setConstants(data);
      } catch (err) {
        console.error("Failed to load constants:", err);
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

  if (constants == null) {
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
          <Config constants={constants} />
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

        {currentView === "controls" && (
          <div style={{ padding: '2rem', color: '#ffffff' }}>
            <h1>Controls Module</h1>
            <p>Advanced control system settings coming soon...</p>
          </div>
        )}

        {currentView === "simulation" && (
          <div style={{ padding: '2rem', color: '#ffffff' }}>
            <h1>Simulation Environment</h1>
            <p>Virtual testing environment coming soon...</p>
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