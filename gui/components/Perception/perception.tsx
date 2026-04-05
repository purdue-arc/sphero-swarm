import { useEffect, useRef, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    faPlay,
    faStop,
    faCircle,
    faVideo,
    faMicrochip,
    faTag,
    faRobot,
    faBolt,
    faSliders,
    faNetworkWired,
} from "@fortawesome/free-solid-svg-icons";
import { StreamViewer } from "../StreamViewer/streamViewer";
import type { PerceptionConfig } from "../../types/swarm_types";
import s from "./perception.module.css";

// ── Types ────────────────────────────────────────────────────────────────────

interface SpheroDetection {
    id: number;
    px: number;
    py: number;
    gx: number;
    gy: number;
}

interface LatencyInfo {
    pipeline_ms: number;
    queue_ms: number;
    e2e_ms: number;
}

interface Telemetry {
    type: string;
    ts: number;
    input_source: string;
    device: string;
    model: string;
    id_mode: string;
    apriltag_count: number;
    perspective_calibrated: boolean;
    zmq_bound: boolean;
    spheros: SpheroDetection[];
    latency: LatencyInfo | null;
}

// ── Constants ────────────────────────────────────────────────────────────────

const MODELS = [
    { label: "bestv3.pt",  value: "./models/bestv3.pt" },
    { label: "bestv2.pt",  value: "./models/bestv2.pt" },
    { label: "yolo11n.pt", value: "./models/yolo11n.pt" },
    { label: "yolov8s.pt", value: "./models/yolov8s.pt" },
];

const IMGSZ_OPTIONS = [320, 416, 640, 1280];
const PERCEPTION_TELEMETRY_PORT = 6770;

const DEFAULT_CONFIG: PerceptionConfig = {
    inputSource: "webcam",
    videoPath: "",
    model: "./models/bestv3.pt",
    conf: 0.25,
    imgsz: 640,
    grid: false,
    locked: false,
    latency: false,
};

// ── Component ────────────────────────────────────────────────────────────────

export function Perception() {
    const [spotterStatus, setSpotterStatus] = useState<"stopped" | "starting" | "started">("stopped");
    const [config, setConfig] = useState<PerceptionConfig>(DEFAULT_CONFIG);
    const [telemetry, setTelemetry] = useState<Telemetry | null>(null);

    const telemetryWsRef    = useRef<WebSocket | null>(null);
    const shouldConnectRef  = useRef(false);
    const reconnectTimerRef = useRef<any>(null);

    // ── Telemetry WebSocket (port 6770) ──────────────────────────────────────
    useEffect(() => {
        shouldConnectRef.current = spotterStatus !== "stopped";

        if (spotterStatus === "stopped") {
            if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
            if (telemetryWsRef.current) {
                telemetryWsRef.current.close();
                telemetryWsRef.current = null;
            }
            setTelemetry(null);
            return;
        }

        const connect = () => {
            if (!shouldConnectRef.current) return;
            const ws = new WebSocket(`ws://localhost:${PERCEPTION_TELEMETRY_PORT}`);
            telemetryWsRef.current = ws;

            ws.onmessage = (e) => {
                try {
                    const data: Telemetry = JSON.parse(e.data);
                    setTelemetry(data);
                    // Transition from "starting" → "started" on first message
                    setSpotterStatus(prev => prev === "starting" ? "started" : prev);
                } catch {
                    // ignore malformed
                }
            };

            ws.onclose = () => {
                telemetryWsRef.current = null;
                if (shouldConnectRef.current) {
                    reconnectTimerRef.current = setTimeout(connect, 500);
                }
            };
        };

        connect();

        return () => {
            shouldConnectRef.current = false;
            if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
            if (telemetryWsRef.current) {
                telemetryWsRef.current.close();
                telemetryWsRef.current = null;
            }
        };
    }, [spotterStatus]);

    // ── Handlers ─────────────────────────────────────────────────────────────
    const handleStart = async () => {
        setSpotterStatus("starting");
        await window.electronAPI.startSpheroSpotter(config);
    };

    const handleStop = async () => {
        setSpotterStatus("stopped");
        setTelemetry(null);
        await window.electronAPI.stopSpheroSpotter();
    };

    const isRunning = spotterStatus !== "stopped";

    const updateConfig = <K extends keyof PerceptionConfig>(key: K, val: PerceptionConfig[K]) => {
        setConfig(prev => ({ ...prev, [key]: val }));
        
        // Send grid toggle command to perception server if grid setting changed while running
        if (key === "grid" && isRunning) {
            console.log(`[Grid Toggle] Grid value changed to: ${val}`);
            console.log(`[Grid Toggle] isRunning: ${isRunning}, WS state: ${telemetryWsRef.current?.readyState}, readyState.OPEN = ${WebSocket.OPEN}`);
            if (telemetryWsRef.current?.readyState === WebSocket.OPEN) {
                try {
                    const msg = JSON.stringify({ action: "toggle_grid" });
                    console.log("[Grid Toggle] Sending:", msg);
                    telemetryWsRef.current.send(msg);
                    console.log("[Grid Toggle] Message sent successfully");
                } catch (e) {
                    console.error("[Grid Toggle] Error sending message:", e);
                }
            } else {
                console.warn("[Grid Toggle] WebSocket not open - retrying in 100ms");
                // Retry after a short delay in case connection is just being established
                setTimeout(() => {
                    if (telemetryWsRef.current?.readyState === WebSocket.OPEN) {
                        try {
                            console.log("[Grid Toggle] Retry: Sending grid toggle command");
                            telemetryWsRef.current.send(JSON.stringify({ action: "toggle_grid" }));
                        } catch (e) {
                            console.error("[Grid Toggle] Retry failed:", e);
                        }
                    }
                }, 100);
            }
        }
    };

    // ── AprilTag colour ───────────────────────────────────────────────────────
    const tagClass =
        !telemetry          ? s.none :
        telemetry.apriltag_count === 4 ? s.full :
        telemetry.apriltag_count > 0   ? s.partial :
        s.none;

    return (
        <div className={s.page}>
            {/* ── Header ──────────────────────────────────────────────────── */}
            <div className={s.header}>
                <div>
                    <h1 className={s.title}>Perception</h1>
                    <p className={s.subtitle}>Vision tracking &amp; arena calibration</p>
                </div>
                <div className={s.headerRight}>
                    <span className={`${s.badge} ${s[spotterStatus]}`}>
                        <FontAwesomeIcon icon={faCircle} className={s.badgeDot} />
                        {spotterStatus === "started"  ? "Running"  :
                         spotterStatus === "starting" ? "Starting" : "Stopped"}
                    </span>
                    {!isRunning ? (
                        <button className={`${s.btn} ${s.btnPrimary}`} onClick={handleStart}>
                            <FontAwesomeIcon icon={faPlay} /> Start
                        </button>
                    ) : (
                        <button
                            className={`${s.btn} ${s.btnDanger}`}
                            onClick={handleStop}
                            disabled={spotterStatus === "starting"}
                        >
                            <FontAwesomeIcon icon={faStop} /> Stop
                        </button>
                    )}
                </div>
            </div>

            {/* ── Main grid ───────────────────────────────────────────────── */}
            <div className={s.mainGrid}>
                {/* Left: Live feed */}
                <div className={s.feedPanel}>
                    <div className={s.panelHeader}>
                        <FontAwesomeIcon icon={faVideo} className={s.panelIcon} />
                        <span className={s.panelTitle}>Live Feed</span>
                        {telemetry && (
                            <span className={`${s.calibBadge} ${telemetry.perspective_calibrated ? s.calibrated : s.uncalibrated}`}>
                                {telemetry.perspective_calibrated ? "Calibrated" : "Uncalibrated"}
                            </span>
                        )}
                    </div>
                    <div className={s.viewerWrap}>
                        <StreamViewer
                            port={6767}
                            serverStatus={spotterStatus}
                            setServerStatus={setSpotterStatus}
                        />
                    </div>
                </div>

                {/* Right: Status cards */}
                <div className={s.statusColumn}>
                    {/* System info */}
                    <div className={s.card}>
                        <div className={s.cardHeader}>
                            <div className={s.cardIcon}><FontAwesomeIcon icon={faMicrochip} /></div>
                            <span className={s.cardTitle}>System</span>
                        </div>
                        <div className={s.infoGrid}>
                            <div className={s.infoItem}>
                                <span className={s.infoLabel}>Device</span>
                                <span className={s.infoValue}>{telemetry?.device ?? "—"}</span>
                            </div>
                            <div className={s.infoItem}>
                                <span className={s.infoLabel}>Source</span>
                                <span className={s.infoValue}>{telemetry?.input_source ?? "—"}</span>
                            </div>
                            <div className={s.infoItem}>
                                <span className={s.infoLabel}>Model</span>
                                <span className={s.infoValue}>{telemetry?.model ?? "—"}</span>
                            </div>
                            <div className={s.infoItem}>
                                <span className={s.infoLabel}>IDs</span>
                                <span className={s.infoValue}>{telemetry?.id_mode ?? "—"}</span>
                            </div>
                        </div>
                    </div>

                    {/* AprilTags */}
                    <div className={s.card}>
                        <div className={s.cardHeader}>
                            <div className={s.cardIcon}><FontAwesomeIcon icon={faTag} /></div>
                            <span className={s.cardTitle}>AprilTags</span>
                        </div>
                        <div className={s.tagRow}>
                            <div className={s.tagCountDisplay}>
                                <span className={`${s.tagNum} ${tagClass}`}>
                                    {telemetry?.apriltag_count ?? 0}
                                </span>
                                <span className={s.tagDenom}>/4</span>
                            </div>
                            <span className={`${s.calibStatus} ${telemetry?.perspective_calibrated ? s.calibOk : s.calibNo}`}>
                                {telemetry?.perspective_calibrated ? "Perspective OK" : "No warp matrix"}
                            </span>
                        </div>
                    </div>

                    {/* ZMQ */}
                    <div className={s.card}>
                        <div className={s.cardHeader}>
                            <div className={s.cardIcon}><FontAwesomeIcon icon={faNetworkWired} /></div>
                            <span className={s.cardTitle}>Algorithm Link — :5555</span>
                        </div>
                        <div className={`${s.zmqRow} ${telemetry?.zmq_bound ? s.zmqOk : s.zmqWaiting}`}>
                            <FontAwesomeIcon icon={faCircle} className={s.zmqDot} />
                            {telemetry?.zmq_bound ? "ZMQ bound — ready for algorithms" : "Waiting to bind..."}
                        </div>
                    </div>

                    {/* Latency (only when flag on and data present) */}
                    {config.latency && telemetry?.latency && (
                        <div className={s.card}>
                            <div className={s.cardHeader}>
                                <div className={s.cardIcon}><FontAwesomeIcon icon={faBolt} /></div>
                                <span className={s.cardTitle}>Latency</span>
                            </div>
                            <div className={s.latencyGrid}>
                                <div className={s.latItem}>
                                    <span className={s.latLabel}>Pipeline</span>
                                    <span className={s.latValue}>{telemetry.latency.pipeline_ms.toFixed(1)}<small> ms</small></span>
                                </div>
                                <div className={s.latItem}>
                                    <span className={s.latLabel}>Queue</span>
                                    <span className={s.latValue}>{telemetry.latency.queue_ms.toFixed(1)}<small> ms</small></span>
                                </div>
                                <div className={s.latItem}>
                                    <span className={s.latLabel}>E2E</span>
                                    <span className={s.latValue}>{telemetry.latency.e2e_ms.toFixed(1)}<small> ms</small></span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* ── Bottom grid ─────────────────────────────────────────────── */}
            <div className={s.bottomGrid}>
                {/* Detections table */}
                <div className={s.card}>
                    <div className={s.cardHeader}>
                        <div className={s.cardIcon}><FontAwesomeIcon icon={faRobot} /></div>
                        <span className={s.cardTitle}>
                            Sphero Detections — {telemetry?.spheros.length ?? 0} tracked
                        </span>
                    </div>
                    {telemetry && telemetry.spheros.length > 0 ? (
                        <table className={s.table}>
                            <thead>
                                <tr>
                                    <th className={s.th}>ID</th>
                                    <th className={s.th}>Pixel (px, py)</th>
                                    <th className={s.th}>Grid (x, y)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {telemetry.spheros.map(sp => (
                                    <tr key={sp.id}>
                                        <td className={s.td}>
                                            <span className={s.idBadge}>{sp.id}</span>
                                        </td>
                                        <td className={s.td}>
                                            <span className={s.mono}>({sp.px}, {sp.py})</span>
                                        </td>
                                        <td className={s.td}>
                                            <span className={s.mono}>({sp.gx.toFixed(2)}, {sp.gy.toFixed(2)})</span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <p className={s.emptyMsg}>
                            {spotterStatus === "started"
                                ? "No Spheros detected in current frame"
                                : "Start perception to see live detections"}
                        </p>
                    )}
                </div>

                {/* Config panel */}
                <div className={s.card}>
                    <div className={s.cardHeader}>
                        <div className={s.cardIcon}><FontAwesomeIcon icon={faSliders} /></div>
                        <span className={s.cardTitle}>Configuration</span>
                    </div>
                    <div className={s.configGrid}>
                        <div className={s.formGroup}>
                            <label className={s.label}>Input Source</label>
                            <select
                                className={s.select}
                                value={config.inputSource}
                                onChange={e => updateConfig("inputSource", e.target.value as any)}
                                disabled={isRunning}
                            >
                                <option value="webcam">Webcam</option>
                                <option value="oakd">OAK-D Camera</option>
                                <option value="video">Video File</option>
                            </select>
                        </div>

                        {config.inputSource === "video" && (
                            <div className={s.formGroup}>
                                <label className={s.label}>Video Path</label>
                                <input
                                    type="text"
                                    className={s.input}
                                    placeholder="./TestVideos/Vid1.mp4"
                                    value={config.videoPath ?? ""}
                                    onChange={e => updateConfig("videoPath", e.target.value)}
                                    disabled={isRunning}
                                />
                            </div>
                        )}

                        <div className={s.formGroup}>
                            <label className={s.label}>YOLO Model</label>
                            <select
                                className={s.select}
                                value={config.model}
                                onChange={e => updateConfig("model", e.target.value)}
                                disabled={isRunning}
                            >
                                {MODELS.map(m => (
                                    <option key={m.value} value={m.value}>{m.label}</option>
                                ))}
                            </select>
                        </div>

                        <div className={s.formGroup}>
                            <label className={s.label}>Confidence — {config.conf.toFixed(2)}</label>
                            <div className={s.sliderRow}>
                                <input
                                    type="range"
                                    className={s.slider}
                                    min={0.05} max={0.95} step={0.05}
                                    value={config.conf}
                                    onChange={e => updateConfig("conf", parseFloat(e.target.value))}
                                    disabled={isRunning}
                                />
                                <span className={s.sliderVal}>{config.conf.toFixed(2)}</span>
                            </div>
                        </div>

                        <div className={s.formGroup}>
                            <label className={s.label}>Image Size</label>
                            <select
                                className={s.select}
                                value={config.imgsz}
                                onChange={e => updateConfig("imgsz", parseInt(e.target.value))}
                                disabled={isRunning}
                            >
                                {IMGSZ_OPTIONS.map(sz => (
                                    <option key={sz} value={sz}>{sz}px</option>
                                ))}
                            </select>
                        </div>

                        <div className={s.formGroup}>
                            <label className={s.label}>Options</label>
                            <div className={s.toggleGroup}>
                                <label className={`${s.toggleItem} ${isRunning ? s.disabled : ""}`}>
                                    <input
                                        type="checkbox"
                                        checked={config.grid}
                                        onChange={e => updateConfig("grid", e.target.checked)}
                                        disabled={false}
                                    />
                                    <span>Grid overlay</span>
                                </label>
                                <label className={`${s.toggleItem} ${isRunning ? s.disabled : ""}`}>
                                    <input
                                        type="checkbox"
                                        checked={config.locked}
                                        onChange={e => updateConfig("locked", e.target.checked)}
                                        disabled={isRunning}
                                    />
                                    <span>Lock IDs after first frame</span>
                                </label>
                                <label className={`${s.toggleItem} ${isRunning ? s.disabled : ""}`}>
                                    <input
                                        type="checkbox"
                                        checked={config.latency}
                                        onChange={e => updateConfig("latency", e.target.checked)}
                                        disabled={isRunning}
                                    />
                                    <span>Show latency metrics (OAK-D only)</span>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
