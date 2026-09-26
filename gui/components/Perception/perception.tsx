import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";
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
    faLayerGroup,
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
    // Present while colour filtering: what the filter is actually running with
    tuning?: { BRIGHT_THRESH: number; BRIGHT_MIN_AREA: number; BRIGHT_BLUR: number };
    mask_streaming?: boolean;
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
const PERCEPTION_FRAME_PORT = 6767;
// Perception only renders the filter mask while something is connected here,
// so mounting/unmounting this viewer is what turns the mask view on and off.
const PERCEPTION_MASK_PORT = 6771;
// How long the slider must sit still before its value is written to disk
const PERSIST_DEBOUNCE_MS = 400;

// ── Component ────────────────────────────────────────────────────────────────

export function Perception({
    spotterStatus,
    setSpotterStatus,
    config,
    setConfig,
}: {
    spotterStatus: "stopped" | "starting" | "started";
    setSpotterStatus: (status: "stopped" | "starting" | "started") => void;
    config: PerceptionConfig;
    setConfig: Dispatch<SetStateAction<PerceptionConfig>>;
}) {
    const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
    const [feedView, setFeedView] = useState<"camera" | "mask">("camera");

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
    // The model is bypassed entirely while colour filtering is on, so its
    // settings are greyed out rather than silently ignored.
    const yoloDisabled = isRunning || config.colorFilter;
    // There is no mask to show unless the colour filter is the detector
    const showMask = config.colorFilter && feedView === "mask";

    // Commands go out on the telemetry socket. It may still be connecting right
    // after a start, so a send that finds it closed is retried a few times.
    const sendCommand = (msg: object, attempt = 0) => {
        const ws = telemetryWsRef.current;
        if (ws?.readyState === WebSocket.OPEN) {
            try {
                ws.send(JSON.stringify(msg));
            } catch (e) {
                console.error("[Perception] Failed to send command:", msg, e);
            }
            return;
        }
        if (attempt < 3) {
            setTimeout(() => sendCommand(msg, attempt + 1), 100);
        } else {
            console.warn("[Perception] Telemetry socket not open, dropped command:", msg);
        }
    };

    // Dragging the slider fires a change per pixel, so the write to
    // constants.json waits for the user to settle on a value.
    const persistTimerRef = useRef<any>(null);
    const persistTuning = (values: Record<string, number | boolean>) => {
        if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
        persistTimerRef.current = setTimeout(() => {
            window.electronAPI
                .savePerceptionTuning(values)
                .catch(e => console.error("[Perception] Failed to save tuning:", e));
        }, PERSIST_DEBOUNCE_MS);
    };

    useEffect(() => () => {
        if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
    }, []);

    const updateConfig = <K extends keyof PerceptionConfig>(key: K, val: PerceptionConfig[K]) => {
        setConfig(prev => ({ ...prev, [key]: val }));

        if (key === "brightThresh") {
            // Saved to gui/constants.json, which is where perception reads its
            // tuning from — so a plain `python sphero_spotter.py -b` picks it up too
            persistTuning({ BRIGHT_THRESH: val as number });
        }

        if (!isRunning) return;

        // Settings that perception can pick up live, without a restart
        if (key === "grid") {
            sendCommand({ action: "toggle_grid" });
        } else if (key === "brightThresh") {
            sendCommand({ action: "set_tuning", values: { BRIGHT_THRESH: val } });
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
                        {config.colorFilter && (
                            <div className={s.viewTabs}>
                                <button
                                    className={`${s.viewTab} ${feedView === "camera" ? s.viewTabActive : ""}`}
                                    onClick={() => setFeedView("camera")}
                                >
                                    <FontAwesomeIcon icon={faVideo} /> Camera
                                </button>
                                <button
                                    className={`${s.viewTab} ${feedView === "mask" ? s.viewTabActive : ""}`}
                                    onClick={() => setFeedView("mask")}
                                >
                                    <FontAwesomeIcon icon={faLayerGroup} /> Pixel mask
                                </button>
                            </div>
                        )}
                        {telemetry && (
                            <span className={`${s.calibBadge} ${telemetry.perspective_calibrated ? s.calibrated : s.uncalibrated}`}>
                                {telemetry.perspective_calibrated ? "Calibrated" : "Uncalibrated"}
                            </span>
                        )}
                    </div>
                    <div className={s.viewerWrap}>
                        {/* One viewer at a time: perception only renders the mask
                            while the mask stream has a client. */}
                        {showMask ? (
                            <StreamViewer
                                key="mask"
                                port={PERCEPTION_MASK_PORT}
                                serverStatus={spotterStatus}
                                setServerStatus={setSpotterStatus}
                                sizing="aspect"
                            />
                        ) : (
                            <StreamViewer
                                key="camera"
                                port={PERCEPTION_FRAME_PORT}
                                serverStatus={spotterStatus}
                                setServerStatus={setSpotterStatus}
                                sizing="aspect"
                            />
                        )}
                    </div>
                    {showMask && (
                        <p className={s.maskHint}>
                            White pixels are above the brightness cutoff. Green boxes are
                            the blobs accepted as spheros; red dots are their centres.
                        </p>
                    )}
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

                        {config.colorFilter && (
                            <div className={s.formGroup}>
                                <label className={s.label}>
                                    Brightness cutoff{isRunning ? " — live" : ""}
                                </label>
                                <div className={s.sliderRow}>
                                    <input
                                        type="range"
                                        className={s.slider}
                                        min={0} max={255} step={1}
                                        value={config.brightThresh}
                                        onChange={e => updateConfig("brightThresh", parseInt(e.target.value))}
                                    />
                                    <span className={s.sliderVal}>{config.brightThresh}</span>
                                </div>
                                <p className={s.fieldHint}>
                                    Pixels at or below this stay black in the mask. Lower it if
                                    spheros are missing, raise it to drop glare. Saved automatically.
                                </p>
                            </div>
                        )}

                        <div className={s.formGroup}>
                            <label className={s.label}>
                                YOLO Model{config.colorFilter ? " — unused (colour filtering on)" : ""}
                            </label>
                            <select
                                className={s.select}
                                value={config.model}
                                onChange={e => updateConfig("model", e.target.value)}
                                disabled={yoloDisabled}
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
                                    disabled={yoloDisabled}
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
                                disabled={yoloDisabled}
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
                                        checked={config.colorFilter}
                                        onChange={e => updateConfig("colorFilter", e.target.checked)}
                                        disabled={isRunning}
                                    />
                                    <span>Colour filtering (instead of YOLO model)</span>
                                </label>
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
