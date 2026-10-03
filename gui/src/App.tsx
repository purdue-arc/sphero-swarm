import { useCallback, useEffect, useState } from 'react'
import styles from './App.module.css'
import { Sidebar } from '../components/Sidebar/sidebar'
import { Runner } from '../components/Runner/runner'
import { Controls } from '../components/Controls/Controls'
import { Config } from '../components/Config/config'
import { Simulation } from '../components/Simulation/simulation'
import { Perception } from '../components/Perception/perception'
import { MainSimulation } from '../components/MainSimulation/MainSimulation'
import type { SpheroConstants, SpheroStatus, PerceptionConfig, SimulationSnapshot } from '../types/swarm_types'

type Reply = { status: string }
declare global {
  interface Window {
    electronAPI: {
      appRenderComplete: () => Promise<unknown>;
      signalAppReady: () => Promise<unknown>;
      getConstants: () => Promise<SpheroConstants>;
      startSpheroSpotter: (config?: PerceptionConfig) => Promise<Reply>;
      stopSpheroSpotter: () => Promise<Reply>;
      restartPerception: (config: PerceptionConfig) => Promise<Reply>;
      startControls: () => Promise<Reply>;
      stopControls: () => Promise<Reply>;
      refreshControls: () => Promise<Reply>;
      getServiceStatus: () => Promise<{ controls: boolean; perception: boolean; algorithm: boolean }>;
      startAlgorithm: () => Promise<Reply>;
      stopAlgorithm: () => Promise<Reply>;
      restartAlgorithm: () => Promise<Reply>;
      quitApp: () => Promise<unknown>;
      saveConstants: (form: SpheroConstants) => Promise<Reply>;
      getPerceptionTuning: () => Promise<Record<string, number | boolean>>;
      savePerceptionTuning: (values: Record<string, number | boolean>) => Promise<unknown>;
    };
  }
}

const DEFAULT_PERCEPTION: PerceptionConfig = {
  inputSource: 'oakd', videoPath: '', model: './models/bestv3.pt', conf: 0.25,
  imgsz: 640, grid: false, locked: false, latency: false, colorFilter: true, brightThresh: 130,
}

function App() {
  const [currentView, setCurrentView] = useState('main')
  const [constants, setConstants] = useState<SpheroConstants | null>(null)
  const [loadError, setLoadError] = useState('')
  const [spheros, setSpheros] = useState<SpheroStatus[]>([])
  const [algorithmRunning, setAlgorithmRunning] = useState(false)
  const [perceptionStatus, setPerceptionStatus] = useState<'stopped' | 'starting' | 'started'>('stopped')
  const [perceptionConfig, setPerceptionConfig] = useState<PerceptionConfig>(DEFAULT_PERCEPTION)
  const [latestSimulationSnapshot, setLatestSimulationSnapshot] = useState<SimulationSnapshot | null>(null)
  const [stepSeconds, setStepSeconds] = useState(4)
  const [useControls, setUseControls] = useState(false)
  const [useAlgorithmColors, setUseAlgorithmColors] = useState(true)

  const updateConstants = useCallback((value: SpheroConstants) => {
    setConstants(value)
    setSpheros(previous => value.SPHERO_TAGS.map((tag, index) => {
      const existing = previous.find(ball => ball.id === tag)
      return {
        id: tag, connection: existing?.connection ?? 'not-attempted',
        actualPosition: existing?.actualPosition ?? [0, 0],
        foundAt: existing?.foundAt,
        batteryPercent: existing?.batteryPercent,
        expectedPosition: value.INITIAL_POSITIONS[index] ?? [0, 0],
      }
    }))
  }, [])

  useEffect(() => {
    window.electronAPI.getConstants().then(value => {
      updateConstants(value)
      window.electronAPI.signalAppReady()
    }).catch(error => { setLoadError(String(error)); window.electronAPI.signalAppReady() })
  }, [updateConstants])

  useEffect(() => {
    let ws: WebSocket | null = null
    let timer: ReturnType<typeof setTimeout> | undefined
    let disposed = false
    const connect = () => {
      if (disposed) return
      ws = new WebSocket('ws://localhost:6769')
      ws.onmessage = event => {
        try { setLatestSimulationSnapshot(JSON.parse(event.data)) } catch { /* malformed frame */ }
      }
      ws.onclose = () => { if (!disposed) timer = setTimeout(connect, 1000) }
      ws.onerror = () => ws?.close()
    }
    connect()
    return () => { disposed = true; clearTimeout(timer); ws?.close() }
  }, [])

  if (!constants) return <div className={styles.loading}>{loadError || 'Loading system...'}</div>
  const simulationProps = {
    constants, latestSnapshot: latestSimulationSnapshot, onSnapshot: setLatestSimulationSnapshot,
    speed: stepSeconds, onSpeedChange: setStepSeconds, useControls,
    hasConnectedSphero: spheros.some(ball => ball.connection === 'connected'),
    onUseControlsChange: setUseControls, useAlgorithmColors, onUseAlgorithmColorsChange: setUseAlgorithmColors,
  }

  return <div className={styles.mainBody}>
    <Sidebar currentView={currentView} setCurrentView={setCurrentView}
      connectedRobots={spheros.filter(s => s.connection === 'connected').length} />
    <main className={styles.viewer}>
      {currentView === 'main' && <MainSimulation constants={constants} setConstants={updateConstants}
        spheros={spheros} setSpheros={setSpheros} algorithmRunning={algorithmRunning} setAlgorithmRunning={setAlgorithmRunning}
        perceptionStatus={perceptionStatus} setPerceptionStatus={setPerceptionStatus}
        perceptionConfig={perceptionConfig} setPerceptionConfig={setPerceptionConfig}
        latestSimulationSnapshot={latestSimulationSnapshot} setLatestSimulationSnapshot={setLatestSimulationSnapshot}
        simulationSpeed={stepSeconds} setSimulationSpeed={setStepSeconds}
        useControls={useControls} setUseControls={setUseControls}
        useAlgorithmColors={useAlgorithmColors} setUseAlgorithmColors={setUseAlgorithmColors} />}
      {currentView === 'dashboard' && <Runner constants={constants} spheros={spheros}
        perceptionStatus={perceptionStatus} setPerceptionStatus={setPerceptionStatus}
        latestSimulationSnapshot={latestSimulationSnapshot} onSimulationSnapshot={setLatestSimulationSnapshot}
        speed={stepSeconds} onSpeedChange={setStepSeconds} useControls={useControls}
        onUseControlsChange={setUseControls} useAlgorithmColors={useAlgorithmColors}
        onUseAlgorithmColorsChange={setUseAlgorithmColors} />}
      {currentView === 'configuration' && <Config constants={constants} onUpdate={updateConstants} algorithmRunning={algorithmRunning} />}
      {currentView === 'controls' && <Controls constants={constants} spheros={spheros} setSpheros={setSpheros} algorithmRunning={algorithmRunning} onAlgorithmStopped={() => setAlgorithmRunning(false)} />}
      {currentView === 'perception' && <Perception spotterStatus={perceptionStatus} setSpotterStatus={setPerceptionStatus}
        config={perceptionConfig} setConfig={setPerceptionConfig} spheroTags={constants.SPHERO_TAGS} />}
      {currentView === 'simulation' && <Simulation {...simulationProps} initialRunning={algorithmRunning} onRunningChange={setAlgorithmRunning} />}
      {currentView === 'algorithms' && <Simulation {...simulationProps} initialRunning={algorithmRunning} onRunningChange={setAlgorithmRunning} />}
      {currentView === 'about' && <div className={styles.legacyPanel}><h1>About Sphero Swarm</h1><p>Swarm control and simulation workspace.</p></div>}
    </main>
  </div>
}

export default App
