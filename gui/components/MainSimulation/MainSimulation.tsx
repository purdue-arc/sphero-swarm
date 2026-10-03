import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowRotateRight, faBrain, faCamera, faCrosshairs, faGear, faPlay, faPlus, faRobot, faStop, faTrash } from '@fortawesome/free-solid-svg-icons'
import { StreamViewer } from '../StreamViewer/streamViewer'
import { useSpheroConnection } from '../SpheroConnection/useSpheroConnection'
import type { PerceptionConfig, SimulationSnapshot, SpheroConstants, SpheroStatus } from '../../types/swarm_types'
import s from './MainSimulation.module.css'

type Status = 'stopped' | 'starting' | 'started'
type Setter<T> = Dispatch<SetStateAction<T>>
interface Props {
  constants: SpheroConstants; setConstants: (value: SpheroConstants) => void;
  spheros: SpheroStatus[]; setSpheros: Setter<SpheroStatus[]>;
  algorithmRunning: boolean; setAlgorithmRunning: Setter<boolean>;
  perceptionStatus: Status; setPerceptionStatus: Setter<Status>;
  perceptionConfig: PerceptionConfig; setPerceptionConfig: Setter<PerceptionConfig>;
  latestSimulationSnapshot: SimulationSnapshot | null; setLatestSimulationSnapshot: Setter<SimulationSnapshot | null>;
  simulationSpeed: number; setSimulationSpeed: Setter<number>;
  useControls: boolean; setUseControls: Setter<boolean>;
  useAlgorithmColors: boolean; setUseAlgorithmColors: Setter<boolean>;
}

const KNOWN_TAGS = ['SB-76B3', 'SB-E274', 'SB-1840', 'SB-B11D', 'SB-CEB2', 'SB-BD0A', 'SB-B5A9', 'SB-E702', 'SB-8262', 'SB-1A8C', 'SB-33C5', 'SB-5AB9', 'SB-D950', 'SB-C596', 'SB-1730', 'SB-41D3', 'SB-3881', 'SB-387B', 'SB-ADA3', 'SB-0439', 'SB-AD19', 'SB-865A', 'SB-4D8E', 'SB-7672', 'SB-7673', 'SB-E1F3']

function sendSocket(port: number, command: object): Promise<void> {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(`ws://localhost:${port}`)
    const timer = window.setTimeout(() => { ws.close(); reject(new Error(`Service on port ${port} did not respond`)) }, 2500)
    ws.onopen = () => {
      ws.send(JSON.stringify(command))
      clearTimeout(timer)
      window.setTimeout(() => ws.close(), 80)
      resolve()
    }
    ws.onerror = () => { clearTimeout(timer); reject(new Error(`Service on port ${port} is unavailable`)) }
  })
}

async function waitForAlgorithm(stepSeconds: number) {
  for (let attempt = 0; attempt < 30; attempt++) {
    try { await sendSocket(6769, { type: 'step_seconds', value: stepSeconds }); return }
    catch { await new Promise(resolve => setTimeout(resolve, 500)) }
  }
  throw new Error('Algorithm service did not become ready')
}

function cssColor(value: string | [number, number, number] | undefined, fallback: string) {
  if (Array.isArray(value) && value.length === 3) return `rgb(${value.join(',')})`
  return typeof value === 'string' && value ? value : fallback
}

type GridPosition = { x: number; y: number }
type BallMotion = { from: GridPosition; to: GridPosition; startedAt: number; duration: number }

function useAnimatedPositions(snapshot: SimulationSnapshot | null, running: boolean, initialPositions: [number, number][], stepSeconds: number, rollSeconds: number) {
  const [positions, setPositions] = useState<Record<number, GridPosition>>({})
  const visible = useRef(new Map<number, GridPosition>())
  const motions = useRef(new Map<number, BallMotion>())

  useEffect(() => {
    if (!running || !snapshot) {
      if (!running) { visible.current.clear(); motions.current.clear() }
      return
    }

    const startedAt = performance.now()
    const duration = Math.max(120, Math.min(900, stepSeconds * 700, rollSeconds * 1000))
    const seen = new Set<number>()
    for (const ball of snapshot.spheros) {
      seen.add(ball.id)
      const target = { x: ball.x, y: ball.y }
      const motion = motions.current.get(ball.id)
      if (motion?.to.x === target.x && motion.to.y === target.y) continue
      const initial = initialPositions[ball.id - 1]
      const current = visible.current.get(ball.id) ?? { x: initial?.[0] ?? target.x, y: initial?.[1] ?? target.y }
      visible.current.set(ball.id, current)
      if (current.x === target.x && current.y === target.y) motions.current.delete(ball.id)
      else motions.current.set(ball.id, { from: current, to: target, startedAt, duration })
    }
    for (const id of visible.current.keys()) {
      if (!seen.has(id)) { visible.current.delete(id); motions.current.delete(id) }
    }

    let frame: number
    const tick = (now: number) => {
      for (const [id, motion] of motions.current) {
        const fraction = Math.min(1, (now - motion.startedAt) / motion.duration)
        const eased = fraction * fraction * (3 - 2 * fraction)
        visible.current.set(id, {
          x: motion.from.x + (motion.to.x - motion.from.x) * eased,
          y: motion.from.y + (motion.to.y - motion.from.y) * eased,
        })
        if (fraction >= 1) motions.current.delete(id)
      }
      setPositions(Object.fromEntries(visible.current))
      if (motions.current.size) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [snapshot, running, initialPositions, stepSeconds, rollSeconds])

  return positions
}

function foundTime(timestamp?: number) {
  return timestamp ? new Date(timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' }) : '—'
}

function fitPositions(positions: [number, number][], width: number, height: number): [number, number][] {
  const occupied = new Set<string>()
  return positions.map(([oldX, oldY]) => {
    let x = Math.max(0, Math.min(width - 1, oldX))
    let y = Math.max(0, Math.min(height - 1, oldY))
    if (occupied.has(`${x}:${y}`)) {
      const free = Array.from({ length: width * height }, (_, index) => [index % width, Math.floor(index / width)] as [number, number])
        .find(([candidateX, candidateY]) => !occupied.has(`${candidateX}:${candidateY}`))
      if (free) [x, y] = free
    }
    occupied.add(`${x}:${y}`)
    return [x, y]
  })
}

export function MainSimulation(p: Props) {
  const [draft, setDraft] = useState(p.constants)
  const selectableTags = [...new Set([...KNOWN_TAGS, ...draft.SPHERO_TAGS])].sort()
  const [selectedBall, setSelectedBall] = useState(0)
  const [saveState, setSaveState] = useState<'saved' | 'saving' | 'error'>('saved')
  const [services, setServices] = useState({ controls: false, perception: false, algorithm: false })
  const [busy, setBusy] = useState(false)
  // Perception starts paused (the camera opens on a white frame) and only
  // detects once told to; every start or restart pauses it again.
  const [detecting, setDetecting] = useState(false)
  const [message, setMessage] = useState('')
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pendingSave = useRef<SpheroConstants | null>(null)
  const saveQueue = useRef<Promise<void>>(Promise.resolve())
  const saveError = useRef<Error | null>(null)
  const runStartedAt = useRef(0)

  const connection = useSpheroConnection(p.spheros, p.setSpheros)
  const { setAlgorithmRunning, setPerceptionStatus, perceptionStatus } = p
  const refreshServices = useCallback(async () => {
    const status = await window.electronAPI.getServiceStatus()
    setServices(status)
    if (!status.algorithm) setAlgorithmRunning(false)
    if (!status.perception && perceptionStatus === 'started') setPerceptionStatus('stopped')
    return status
  }, [setAlgorithmRunning, setPerceptionStatus, perceptionStatus])
  useEffect(() => {
    void refreshServices().catch(() => undefined)
    const timer = window.setInterval(() => { void refreshServices().catch(() => undefined) }, 3000)
    return () => window.clearInterval(timer)
  }, [refreshServices])

  const persistSettings = (): Promise<void> => {
    if (saveTimer.current) { clearTimeout(saveTimer.current); saveTimer.current = null }
    const value = pendingSave.current
    if (!value) return saveQueue.current
    pendingSave.current = null
    const tags = value.SPHERO_TAGS.map(tag => tag.trim().toUpperCase())
    if (tags.some(tag => !tag) || new Set(tags).size !== tags.length) {
      const error = new Error('Every Sphero needs a unique tag before settings can be saved')
      saveError.current = error
      setSaveState('error')
      return Promise.reject(error)
    }
    setSaveState('saving')
    const operation = saveQueue.current.then(async () => {
      await window.electronAPI.saveConstants(value)
      if (!p.algorithmRunning) {
        try { await sendSocket(6769, { type: 'reset' }) } catch { /* preview remains available locally while the service is offline */ }
      }
      saveError.current = null
      if (!pendingSave.current) setSaveState('saved')
    }).catch(error => {
      saveError.current = error instanceof Error ? error : new Error(String(error))
      setSaveState('error')
      throw error
    })
    saveQueue.current = operation.catch(() => undefined)
    return operation
  }
  const changeSettings = (next: SpheroConstants) => {
    setDraft(next)
    p.setConstants(next)
    pendingSave.current = next
    saveError.current = null
    setSaveState('saving')
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = window.setTimeout(() => { void persistSettings().catch(error => setMessage(String(error))) }, 450)
  }
  const flushSettings = async () => {
    if (pendingSave.current) await persistSettings()
    await saveQueue.current
    if (saveError.current) throw saveError.current
  }
  useEffect(() => () => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    if (pendingSave.current) {
      const value = pendingSave.current
      pendingSave.current = null
      const tags = value.SPHERO_TAGS.map(tag => tag.trim().toUpperCase())
      if (tags.every(Boolean) && new Set(tags).size === tags.length) {
        void saveQueue.current.then(() => window.electronAPI.saveConstants(value)).catch(() => undefined)
      }
    }
  }, [])

  const updateGrid = (field: 'GRID_WIDTH' | 'GRID_HEIGHT', raw: number) => {
    const other = field === 'GRID_WIDTH' ? draft.GRID_HEIGHT : draft.GRID_WIDTH
    const minimum = Math.max(2, Math.ceil(draft.N_SPHEROS / other))
    const size = Math.max(minimum, Math.min(30, Math.round(raw || minimum)))
    const width = field === 'GRID_WIDTH' ? size : draft.GRID_WIDTH
    const height = field === 'GRID_HEIGHT' ? size : draft.GRID_HEIGHT
    changeSettings({ ...draft, [field]: size,
      INITIAL_POSITIONS: fitPositions(draft.INITIAL_POSITIONS, width, height) })
  }
  const updateTag = (index: number, tag: string) => {
    const tags = [...draft.SPHERO_TAGS]
    const nextTag = tag.toUpperCase()
    const previousOwner = tags.findIndex((candidate, i) => i !== index && candidate === nextTag)
    if (previousOwner !== -1) {
      if (p.spheros.some(ball => ball.id === nextTag && ball.connection === 'connected')) {
        setMessage('Disconnect that Sphero before changing its assignment')
        return
      }
      tags[previousOwner] = tags[index]
    }
    tags[index] = nextTag
    changeSettings({ ...draft, SPHERO_TAGS: tags })
  }
  const moveBall = (index: number, x: number, y: number) => {
    const positions = draft.INITIAL_POSITIONS.map(position => [...position] as [number, number])
    const old = positions[index]
    const occupant = positions.findIndex((position, i) => i !== index && position[0] === x && position[1] === y)
    if (occupant >= 0) positions[occupant] = old
    positions[index] = [x, y]
    changeSettings({ ...draft, INITIAL_POSITIONS: positions })
  }
  const updateTrait = (index: number, trait: 'head' | 'tail') => {
    const traits = [...draft.INITIAL_TRAITS]
    traits[index] = trait
    if (!traits.includes('head')) traits[0] = 'head'
    changeSettings({ ...draft, INITIAL_TRAITS: traits })
  }
  const addBall = () => {
    if (draft.N_SPHEROS >= draft.GRID_WIDTH * draft.GRID_HEIGHT) return
    const tag = KNOWN_TAGS.find(candidate => !draft.SPHERO_TAGS.includes(candidate)) ?? `SB-${(draft.N_SPHEROS + 1).toString(16).padStart(4, '0').toUpperCase()}`
    const used = new Set(draft.INITIAL_POSITIONS.map(([x, y]) => `${x}:${y}`))
    let position: [number, number] = [0, 0]
    for (let y = 0; y < draft.GRID_HEIGHT; y++) {
      for (let x = 0; x < draft.GRID_WIDTH; x++) {
        if (!used.has(`${x}:${y}`)) { position = [x, y]; y = draft.GRID_HEIGHT; break }
      }
    }
    changeSettings({ ...draft, N_SPHEROS: draft.N_SPHEROS + 1,
      SPHERO_TAGS: [...draft.SPHERO_TAGS, tag], INITIAL_POSITIONS: [...draft.INITIAL_POSITIONS, position],
      INITIAL_TRAITS: [...draft.INITIAL_TRAITS, 'tail'] })
    setSelectedBall(draft.N_SPHEROS)
  }
  const removeBall = (index: number) => {
    if (draft.N_SPHEROS <= 1) return
    const traits = draft.INITIAL_TRAITS.filter((_, i) => i !== index)
    if (!traits.includes('head')) traits[0] = 'head'
    changeSettings({ ...draft, N_SPHEROS: draft.N_SPHEROS - 1,
      SPHERO_TAGS: draft.SPHERO_TAGS.filter((_, i) => i !== index),
      INITIAL_POSITIONS: draft.INITIAL_POSITIONS.filter((_, i) => i !== index), INITIAL_TRAITS: traits })
    setSelectedBall(current => Math.min(current, draft.N_SPHEROS - 2))
  }

  const act = async (action: () => Promise<void>) => {
    setBusy(true); setMessage('')
    try { await action(); await refreshServices() }
    catch (error) { setMessage(error instanceof Error ? error.message : String(error)) }
    finally { setBusy(false) }
  }
  const connectAll = () => act(async () => {
    await flushSettings()
    const result = await window.electronAPI.startControls()
    if (result.status === 'failed') throw new Error('Controls service failed to start')
    connection.startConnection()
  })
  const restartControls = () => act(async () => {
    if (p.algorithmRunning) {
      await window.electronAPI.restartAlgorithm()
      p.setAlgorithmRunning(false)
      p.setLatestSimulationSnapshot(null)
    }
    const result = await window.electronAPI.refreshControls()
    if (result.status !== 'started') throw new Error('Controls service failed to restart')
    connection.resetConnection()
  })
  const disconnectBall = (tag: string) => act(async () => {
    if (p.algorithmRunning) { await sendSocket(6769, { type: 'reset' }); p.setAlgorithmRunning(false) }
    await sendSocket(6768, { type: 'disconnect', ball: tag })
    p.setSpheros(previous => previous.map(ball => ball.id === tag ? { ...ball, connection: 'not-attempted', foundAt: undefined, batteryPercent: undefined } : ball))
  })
  const retryBall = (tag: string) => { connection.retryConnection(tag) }

  const startAlgorithm = () => act(async () => {
    await flushSettings()
    const status = await window.electronAPI.getServiceStatus()
    if (p.useControls && (!status.controls || !p.spheros.some(ball => ball.connection === 'connected'))) {
      throw new Error('Connect a Sphero before enabling hardware movement')
    }
    if (!status.algorithm) await window.electronAPI.startAlgorithm()
    await waitForAlgorithm(p.simulationSpeed)
    await sendSocket(6769, { type: 'use_controls', value: p.useControls })
    await sendSocket(6769, { type: 'use_algorithm_colors', value: p.useAlgorithmColors })
    runStartedAt.current = Date.now()
    await sendSocket(6769, { type: 'start', step_seconds: p.simulationSpeed })
    p.setAlgorithmRunning(true)
  })
  const stopAlgorithm = () => act(async () => {
    await sendSocket(6769, { type: 'reset' })
    p.setAlgorithmRunning(false)
  })
  const restartAlgorithm = () => act(async () => {
    await window.electronAPI.restartAlgorithm()
    p.setAlgorithmRunning(false)
    p.setLatestSimulationSnapshot(null)
  })

  const setSource = (source: 'oakd' | 'webcam') => act(async () => {
    const next = { ...p.perceptionConfig, inputSource: source }
    p.setPerceptionConfig(next)
    if (p.perceptionStatus !== 'stopped') {
      p.setPerceptionStatus('starting')
      await window.electronAPI.restartPerception(next)
    }
  })
  const toggleGrid = (checked: boolean) => act(async () => {
    p.setPerceptionConfig(previous => ({ ...previous, grid: checked }))
    if (p.perceptionStatus !== 'stopped') await sendSocket(6770, { action: 'toggle_grid' })
  })
  const startPerception = () => act(async () => {
    const config = { ...p.perceptionConfig, inputSource: p.perceptionConfig.inputSource === 'webcam' ? 'webcam' as const : 'oakd' as const }
    p.setPerceptionConfig(config)
    p.setPerceptionStatus('starting')
    try { await window.electronAPI.startSpheroSpotter(config) }
    catch (error) { p.setPerceptionStatus('stopped'); throw error }
  })
  useEffect(() => { if (perceptionStatus !== 'started') setDetecting(false) }, [perceptionStatus])
  const startDetection = () => act(async () => {
    await sendSocket(6770, { action: 'start_detection' })
    setDetecting(true)
  })
  const stopPerception = () => act(async () => {
    p.setPerceptionStatus('stopped')
    await window.electronAPI.stopSpheroSpotter()
  })
  const restartPerception = () => act(async () => {
    const config = { ...p.perceptionConfig, inputSource: p.perceptionConfig.inputSource === 'webcam' ? 'webcam' as const : 'oakd' as const }
    p.setPerceptionConfig(config)
    p.setPerceptionStatus('starting')
    try { await window.electronAPI.restartPerception(config) }
    catch (error) { p.setPerceptionStatus('stopped'); throw error }
  })

  const width = Math.max(2, draft.GRID_WIDTH)
  const height = Math.max(2, draft.GRID_HEIGHT)
  const plotX = (x: number) => 44 + (x / (width - 1)) * 552
  const plotY = (y: number) => 48 + (y / (height - 1)) * 284
  const liveSnapshot = p.algorithmRunning && p.latestSimulationSnapshot && p.latestSimulationSnapshot.timestamp * 1000 >= runStartedAt.current
    ? p.latestSimulationSnapshot : null
  const animatedPositions = useAnimatedPositions(liveSnapshot, p.algorithmRunning, draft.INITIAL_POSITIONS, p.simulationSpeed, draft.ROLL_DURATION)
  const plottedBalls = liveSnapshot
    ? liveSnapshot.spheros.map(ball => {
      const visual = animatedPositions[ball.id] ?? {
        x: draft.INITIAL_POSITIONS[ball.id - 1]?.[0] ?? ball.x,
        y: draft.INITIAL_POSITIONS[ball.id - 1]?.[1] ?? ball.y,
      }
      return { id: ball.id, x: visual.x, y: visual.y,
        color: cssColor(ball.color, '#a78bfa'), tag: draft.SPHERO_TAGS[ball.id - 1] ?? '' }
    })
    : draft.INITIAL_POSITIONS.map(([x, y], index) => ({ id: index + 1, x, y,
      color: draft.INITIAL_TRAITS[index] === 'head' ? '#ef4444' : '#3b82f6', tag: draft.SPHERO_TAGS[index] ?? '' }))
  const positions = new Map(plottedBalls.map(ball => [ball.id, ball]))
  const bonds = liveSnapshot?.bonded_groups.flatMap(group => group.flatMap((a, index) => group.slice(index + 1).map(b => [a, b] as const))) ?? []
  const connectedCount = p.spheros.filter(ball => ball.connection === 'connected').length

  return <div className={s.page}>
    <header className={s.topbar}>
      <div className={s.brand}><strong>Runner</strong></div>
      <div className={s.overview}><span><i className={services.algorithm ? s.dotOn : s.dot} /> Algorithm {services.algorithm ? 'online' : 'offline'}</span>
        <span><i className={connectedCount ? s.dotOn : s.dot} /> {connectedCount}/{p.spheros.length} connected</span>
        <span className={s.savedState}>{saveState === 'saved' ? 'Settings saved' : saveState === 'saving' ? 'Saving settings…' : 'Settings need attention'}</span></div>
    </header>
    {message && <div className={s.message} role="alert">{message}<button onClick={() => setMessage('')} aria-label="Dismiss message">×</button></div>}

    <div className={s.quarters}>
      <section className={`${s.panel} ${s.settingsPanel}`} aria-label="Settings">
        <div className={s.panelHead}><span className={s.panelIcon}><FontAwesomeIcon icon={faGear} /></span><h2>Settings</h2></div>
        <div className={s.panelBody}>
          <div className={s.gridControls}><span className={s.fieldTitle}>GRID SIZE</span>
            <label>Columns <input type="number" min="2" max="30" value={draft.GRID_WIDTH} disabled={p.algorithmRunning} onChange={e => updateGrid('GRID_WIDTH', Number(e.target.value))} /></label>
            <span className={s.multiply}>×</span>
            <label>Rows <input type="number" min="2" max="30" value={draft.GRID_HEIGHT} disabled={p.algorithmRunning} onChange={e => updateGrid('GRID_HEIGHT', Number(e.target.value))} /></label>
          </div>
          <div className={s.tableHeading}><span>SPHERO BALLS</span><span>{draft.N_SPHEROS} TOTAL</span></div>
          <div className={s.tableWrap}><table className={s.settingsTable}><thead><tr><th>ID</th><th>Sphero tag</th><th>X</th><th>Y</th><th>Role</th><th></th></tr></thead>
            <tbody>{draft.SPHERO_TAGS.map((tag, index) => <tr key={index} className={selectedBall === index ? s.selectedRow : ''}>
              <td><button className={`${s.ballIndex} ${draft.INITIAL_TRAITS[index] === 'head' ? s.ballIndexHead : s.ballIndexTail}`} onClick={() => setSelectedBall(index)} aria-label={`Select ball ${index + 1}`}>{String(index + 1).padStart(2, '0')}</button></td>
              <td><select className={s.tagInput} aria-label={`Tag for ball ${index + 1}`} value={tag} disabled={p.algorithmRunning || p.spheros.some(ball => ball.id === tag && ball.connection === 'connected')} onChange={e => updateTag(index, e.target.value)}>
                {selectableTags.map(candidate => <option key={candidate} value={candidate} disabled={candidate !== tag && p.spheros.some(ball => ball.id === candidate && ball.connection === 'connected')}>{candidate}</option>)}
              </select></td>
              <td><input className={s.cellNumber} type="number" min="0" max={width - 1} aria-label={`X position for ball ${index + 1}`} value={draft.INITIAL_POSITIONS[index]?.[0] ?? 0} disabled={p.algorithmRunning} onChange={e => moveBall(index, Math.max(0, Math.min(width - 1, Number(e.target.value))), draft.INITIAL_POSITIONS[index]?.[1] ?? 0)} /></td>
              <td><input className={s.cellNumber} type="number" min="0" max={height - 1} aria-label={`Y position for ball ${index + 1}`} value={draft.INITIAL_POSITIONS[index]?.[1] ?? 0} disabled={p.algorithmRunning} onChange={e => moveBall(index, draft.INITIAL_POSITIONS[index]?.[0] ?? 0, Math.max(0, Math.min(height - 1, Number(e.target.value))))} /></td>
              <td><label className={s.roleSwitch} title={draft.INITIAL_TRAITS[index] === 'head' && draft.INITIAL_TRAITS.filter(trait => trait === 'head').length === 1 ? 'At least one head is required' : undefined}>
                <input type="checkbox" checked={draft.INITIAL_TRAITS[index] === 'head'} aria-label={`Ball ${index + 1} head or tail`} disabled={p.algorithmRunning || (draft.INITIAL_TRAITS[index] === 'head' && draft.INITIAL_TRAITS.filter(trait => trait === 'head').length === 1)} onChange={e => updateTrait(index, e.target.checked ? 'head' : 'tail')} />
                <span className={s.roleTrack} /><span>{draft.INITIAL_TRAITS[index] === 'head' ? 'Head' : 'Tail'}</span></label></td>
              <td><button className={s.rowAction} disabled={p.algorithmRunning || draft.N_SPHEROS <= 1} aria-label={`Remove ball ${index + 1}`} onClick={() => removeBall(index)}><FontAwesomeIcon icon={faTrash} /></button></td>
            </tr>)}</tbody></table></div>
          <button className={s.addButton} onClick={addBall} disabled={p.algorithmRunning || draft.N_SPHEROS >= width * height}><FontAwesomeIcon icon={faPlus} /> Add Sphero</button>
          <p className={s.inlineHint}>Choose a ball, then click a node in the algorithm preview to place it.</p>
        </div>
      </section>

      <section className={`${s.panel} ${s.controlsPanel}`} aria-label="Controls">
        <div className={s.panelHead}><span className={s.panelIcon}><FontAwesomeIcon icon={faRobot} /></span><h2>Controls</h2></div>
        <div className={s.panelBody}>
          <div className={s.controlSummary}><strong>{connectedCount}<span> / {p.spheros.length}</span></strong><span>Spheros connected</span><i className={services.controls ? s.statusGood : s.statusMuted}>{services.controls ? 'SERVICE ONLINE' : 'SERVICE OFFLINE'}</i></div>
          <div className={s.buttonRow}><button className={s.primary} disabled={busy || connection.connectState !== 'idle'} onClick={() => void connectAll()}><FontAwesomeIcon icon={faPlay} /> Connect all</button>
            <button className={s.subtle} disabled={busy || connectedCount === 0} onClick={() => void restartControls()}>Disconnect all</button>
            <button className={s.iconButton} disabled={busy} onClick={() => void restartControls()} title="Restart controls service" aria-label="Restart controls service"><FontAwesomeIcon icon={faArrowRotateRight} /></button></div>
          <div className={s.tableWrap}><table className={s.connectionTable}><thead><tr><th>ID</th><th>Sphero</th><th>Status</th><th>Found</th><th>Charge</th><th>Action</th></tr></thead>
            <tbody>{p.spheros.map((ball, index) => <tr key={ball.id}><td className={s.mutedId}>{String(index + 1).padStart(2, '0')}</td><td className={s.mono}>{ball.id}</td>
              <td><span className={`${s.connectionBadge} ${s[ball.connection] ?? ''}`}><i />{ball.connection === 'not-attempted' ? 'Ready' : ball.connection === 'pending' ? 'Scanning' : ball.connection === 'found' ? 'Found' : ball.connection === 'connected' ? 'Connected' : 'Failed'}</span></td>
              <td className={s.foundTime}>{ball.foundAt ? <time dateTime={new Date(ball.foundAt).toISOString()} title={new Date(ball.foundAt).toLocaleString()}>{foundTime(ball.foundAt)}</time> : '—'}</td>
              <td className={s.foundTime}>{ball.connection === 'connected' && ball.batteryPercent !== undefined ? `${ball.batteryPercent}%` : '—'}</td>
              <td>{ball.connection === 'connected' ? <button className={s.tableAction} disabled={busy} onClick={() => void disconnectBall(ball.id)}>Disconnect</button>
                : ball.connection === 'failed' || (ball.connection === 'not-attempted' && connection.connectState !== 'idle') ? <button className={s.tableAction} disabled={busy || !services.controls} onClick={() => retryBall(ball.id)}>Retry</button> : <span className={s.emptyAction}>—</span>}</td></tr>)}</tbody></table></div>
        </div>
      </section>

      <section className={`${s.panel} ${s.algorithmPanel}`} aria-label="Algorithms">
        <div className={s.panelHead}><span className={s.panelIcon}><FontAwesomeIcon icon={faBrain} /></span><h2>Algorithms</h2></div>
        <div className={s.algorithmBody}>
          <div className={s.boardTop}><span><i className={p.algorithmRunning ? s.dotOn : s.dot} /> {p.algorithmRunning ? 'SIMULATION RUNNING' : 'STARTING POSITIONS'}</span><span>{width} × {height} GRID</span></div>
          <div className={s.board}><svg viewBox="0 0 640 380" role="img" aria-label="Sphero positions on the simulation grid" preserveAspectRatio="xMidYMid meet">
            <defs><filter id="ballGlow"><feGaussianBlur stdDeviation="5" /></filter></defs>
            {Array.from({ length: width }, (_, x) => <line key={`v${x}`} className={s.gridLine} x1={plotX(x)} x2={plotX(x)} y1="48" y2="332" />)}
            {Array.from({ length: height }, (_, y) => <line key={`h${y}`} className={s.gridLine} x1="44" x2="596" y1={plotY(y)} y2={plotY(y)} />)}
            {Array.from({ length: width }, (_, x) => Array.from({ length: height }, (_, y) => <g key={`${x}:${y}`}><circle cx={plotX(x)} cy={plotY(y)} r="3" className={s.gridNode} />
              {!p.algorithmRunning && <circle cx={plotX(x)} cy={plotY(y)} r="13" fill="transparent" className={s.nodeTarget} role="button" aria-label={`Place selected ball at ${x}, ${y}`} onClick={() => moveBall(selectedBall, x, y)} />}</g>))}
            {bonds.map(([a, b]) => { const from = positions.get(a), to = positions.get(b); return from && to ? <line key={`${a}-${b}`} className={s.bond} x1={plotX(from.x)} y1={plotY(from.y)} x2={plotX(to.x)} y2={plotY(to.y)} /> : null })}
            {plottedBalls.map(ball => <g key={ball.id} className={s.plottedBall} onClick={() => !p.algorithmRunning && setSelectedBall(ball.id - 1)}>
              <circle cx={plotX(ball.x)} cy={plotY(ball.y)} r="18" fill={ball.color} opacity=".35" filter="url(#ballGlow)" />
              <circle cx={plotX(ball.x)} cy={plotY(ball.y)} r="14" fill="none" stroke={draft.INITIAL_TRAITS[ball.id - 1] === 'head' ? '#ef4444' : '#3b82f6'} strokeWidth="2" />
              <circle cx={plotX(ball.x)} cy={plotY(ball.y)} r="11" fill={ball.color} stroke={selectedBall === ball.id - 1 && !p.algorithmRunning ? '#ffffff' : '#dff8f6'} strokeWidth="2" />
              <text x={plotX(ball.x)} y={plotY(ball.y) - 19} textAnchor="middle" className={s.ballLabel}>{p.algorithmRunning ? `#${ball.id}` : `${ball.id} · ${ball.tag}`}</text>
            </g>)}
          </svg></div>
          <div className={s.algorithmToolbar}><button className={s.primary} disabled={busy || p.algorithmRunning} onClick={() => void startAlgorithm()}><FontAwesomeIcon icon={faPlay} /> Start</button>
            <button className={s.subtle} disabled={busy || !p.algorithmRunning} onClick={() => void stopAlgorithm()}><FontAwesomeIcon icon={faStop} /> Stop</button>
            <button className={s.iconButton} disabled={busy} onClick={() => void restartAlgorithm()} title="Restart algorithm service" aria-label="Restart algorithm service"><FontAwesomeIcon icon={faArrowRotateRight} /></button>
            <label className={s.smallToggle}><input type="checkbox" checked={p.useControls} disabled={p.algorithmRunning} onChange={e => p.setUseControls(e.target.checked)} /> Use controls</label>
            <label className={s.speedControl}>Step seconds <input type="range" min="0.1" max="10" step="0.1" value={p.simulationSpeed} onChange={e => { const value = Number(e.target.value); p.setSimulationSpeed(value); if (p.algorithmRunning) void sendSocket(6769, { type: 'step_seconds', value }).catch(error => setMessage(String(error))) }} /><b>{p.simulationSpeed.toFixed(1)} s</b></label></div>
        </div>
      </section>

      <section className={`${s.panel} ${s.perceptionPanel}`} aria-label="Perception">
        <div className={s.panelHead}><span className={s.panelIcon}><FontAwesomeIcon icon={faCamera} /></span><h2>Perception</h2></div>
        <div className={s.perceptionBody}>
          <div className={s.cameraControls}><label>Camera <select value={p.perceptionConfig.inputSource === 'webcam' ? 'webcam' : 'oakd'} disabled={busy} onChange={e => void setSource(e.target.value as 'oakd' | 'webcam')}><option value="oakd">OAK-D</option><option value="webcam">Webcam</option></select></label>
            <label className={s.gridSwitch}><input type="checkbox" checked={p.perceptionConfig.grid} disabled={busy} onChange={e => void toggleGrid(e.target.checked)} /> Display grid lines</label></div>
          <div className={s.cameraFrame}><StreamViewer port={6767} serverStatus={p.perceptionStatus} setServerStatus={p.setPerceptionStatus} showStats={false} /></div>
          <div className={s.cameraFooter}><span><i className={p.perceptionStatus === 'started' ? s.dotOn : s.dot} />{p.perceptionStatus === 'started' ? 'CAMERA LIVE' : p.perceptionStatus === 'starting' ? 'STARTING CAMERA' : 'CAMERA OFFLINE'}</span>
            <div className={s.buttonRow}>{p.perceptionStatus === 'stopped' ? <button className={s.primary} disabled={busy} onClick={() => void startPerception()}><FontAwesomeIcon icon={faPlay} /> Start</button>
              : <>{!detecting && <button className={s.primary} disabled={busy || p.perceptionStatus !== 'started'} onClick={() => void startDetection()} title="Start finding Spheros once the camera picture has settled"><FontAwesomeIcon icon={faCrosshairs} /> Start detecting</button>}
                <button className={s.subtle} disabled={busy} onClick={() => void stopPerception()}><FontAwesomeIcon icon={faStop} /> Stop</button></>}
              <button className={s.iconButton} disabled={busy} onClick={() => void restartPerception()} title="Restart perception service" aria-label="Restart perception service"><FontAwesomeIcon icon={faArrowRotateRight} /></button></div></div>
        </div>
      </section>
    </div>
  </div>
}
