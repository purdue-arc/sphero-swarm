import { useEffect, useState, useRef } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCircle, faVideoSlash } from "@fortawesome/free-solid-svg-icons";
import styles from "./streamViewer.module.css";
import type { SimulationSnapshot } from "../../types/swarm_types";

type StreamStatus = "stopped" | "starting" | "started";

function formatAngle(angle: number) {
    const rounded = Math.round(angle);
    return `${rounded > 0 ? "+" : ""}${rounded}°`;
}

// Tallest the feed may get in "aspect" sizing, so it always fits the window
const MAX_FEED_VH = 62;
const FALLBACK_ASPECT = 16 / 9;

export function StreamViewer({
    port,
    serverStatus,
    setServerStatus,
    sizing = "fill",
    showStats = true,
    latestSimulationSnapshot,
    showCorrectionVectors = false,
}: {
    port: number;
    serverStatus: string;
    setServerStatus: (status: StreamStatus) => void;
    /**
     * "fill"   — fill whatever box the parent gives it (fixed-height panels).
     * "aspect" — size to the stream's own aspect ratio, as wide as the parent
     *            allows and capped by window height, so there are no black bars.
     */
    sizing?: "fill" | "aspect";
    showStats?: boolean;
    latestSimulationSnapshot?: SimulationSnapshot | null;
    showCorrectionVectors?: boolean;
}) {
    const [imageSrc, setImageSrc] = useState<string>("");
    const [frameCount, setFrameCount] = useState<number>(0);
    const [fps, setFps] = useState<number>(0);
    // Read off the decoded frame, so it follows whichever stream is connected
    const [resolution, setResolution] = useState<string | null>(null);
    const [aspect, setAspect] = useState<number | null>(null);
    
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const shouldConnectRef = useRef<boolean>(false);
    const fpsIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const frameCountRef = useRef<number>(0);

    // FPS calculation
    useEffect(() => {
        if (serverStatus === "started") {
            fpsIntervalRef.current = setInterval(() => {
                setFps(frameCountRef.current);
                frameCountRef.current = 0;
            }, 1000);
        } else {
            if (fpsIntervalRef.current) {
                clearInterval(fpsIntervalRef.current);
                fpsIntervalRef.current = null;
            }
            frameCountRef.current = 0;
        }

        return () => {
            if (fpsIntervalRef.current) {
                clearInterval(fpsIntervalRef.current);
            }
        };
    }, [serverStatus]);

    const active = serverStatus !== "stopped";
    useEffect(() => {
        shouldConnectRef.current = active;

        if (!active) {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
            }

            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }

            return;
        }

        const connect = () => {
            // Double-check before connecting
            if (!shouldConnectRef.current) return;

            wsRef.current = new WebSocket(`ws://localhost:${port}`);

            wsRef.current.onopen = () => {
                console.log("WebSocket connected");
            };

            wsRef.current.onmessage = (event: MessageEvent) => {
                if (!shouldConnectRef.current) return;
                setImageSrc(`data:image/jpeg;base64,${event.data}`);
                frameCountRef.current++;
                setFrameCount(prev => prev + 1);
                setServerStatus("started");
            };

            wsRef.current.onerror = (error: Event) => {
                console.error("WebSocket error:", error);
            };

            wsRef.current.onclose = () => {
                console.log("WebSocket disconnected");
                wsRef.current = null;

                // Only reconnect if we should still be connected
                if (shouldConnectRef.current) {
                    reconnectTimeoutRef.current = setTimeout(connect, 500);
                }
            };
        };

        connect();

        return () => {
            // Mark that we shouldn't reconnect
            shouldConnectRef.current = false;

            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
            }

            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [active, port, setServerStatus]);

    // Box matches the stream's own shape, so no part of the panel is wasted on
    // black bars. maxWidth is what keeps the height under MAX_FEED_VH: capping
    // the height alone would leave the box wide and bar the sides instead.
    const feedAspect = aspect ?? FALLBACK_ASPECT;
    const aspectStyle = {
        flex: "0 0 auto",
        width: "100%",
        aspectRatio: String(feedAspect),
        maxWidth: `calc(${MAX_FEED_VH}vh * ${feedAspect})`,
        margin: "0 auto",
    } as const;
    // Keep the stat bar the same width as the feed above it
    const barStyle = {
        width: "100%",
        maxWidth: aspectStyle.maxWidth,
        margin: "0 auto",
    } as const;

    const correctionSpheros = latestSimulationSnapshot?.spheros.filter(
        sphero => sphero.correction_debug !== undefined && sphero.correction_debug !== null
    ) ?? [];
    const gridWidth = Math.max(1, (latestSimulationSnapshot?.grid.width ?? 2) - 1);
    const gridHeight = Math.max(1, (latestSimulationSnapshot?.grid.height ?? 2) - 1);
    const shouldShowCorrections = showCorrectionVectors && correctionSpheros.length > 0;

    return (
        <div className={styles.streamViewer}>
            <div
                className={`${styles.imageViewer} ${
                    serverStatus !== "stopped" ? styles.active : ""
                }`}
                style={sizing === "aspect" ? aspectStyle : undefined}
            >
                {serverStatus !== "started" ? (
                    <div className={styles.imagePlaceholder}>
                        {serverStatus === "starting" ? (
                            <>
                                <div className={styles.loadingSpinner}></div>
                                <p className={styles.placeholderText}>
                                    Initializing camera feed...
                                </p>
                            </>
                        ) : (
                            <>
                                <FontAwesomeIcon
                                    icon={faVideoSlash}
                                    className={styles.placeholderIcon}
                                />
                                <p className={styles.placeholderText}>
                                    Camera feed inactive
                                </p>
                            </>
                        )}
                    </div>
                ) : (
                    <>
                        <div className={styles.frameSurface}>
                            <img
                                src={imageSrc}
                                alt="Camera feed"
                                onLoad={e => {
                                    const img = e.currentTarget;
                                    if (!img.naturalWidth || !img.naturalHeight) return;
                                    const dims = `${img.naturalWidth}×${img.naturalHeight}`;
                                    setResolution(prev => (prev === dims ? prev : dims));
                                    const a = img.naturalWidth / img.naturalHeight;
                                    setAspect(prev => (prev !== null && Math.abs(prev - a) < 0.001 ? prev : a));
                                }}
                            />
                            {shouldShowCorrections && (
                                <svg
                                    className={styles.correctionOverlay}
                                    viewBox={`0 0 ${gridWidth} ${gridHeight}`}
                                    preserveAspectRatio="none"
                                    aria-hidden="true"
                                >
                                    <defs>
                                        <marker
                                            id="previous-vector-arrow"
                                            viewBox="0 0 10 10"
                                            refX="8"
                                            refY="5"
                                            markerWidth="8"
                                            markerHeight="8"
                                            orient="auto-start-reverse"
                                        >
                                            <path d="M 0 0 L 10 5 L 0 10 z" className={styles.previousMarker} />
                                        </marker>
                                        <marker
                                            id="projected-vector-arrow"
                                            viewBox="0 0 10 10"
                                            refX="8"
                                            refY="5"
                                            markerWidth="8"
                                            markerHeight="8"
                                            orient="auto-start-reverse"
                                        >
                                            <path d="M 0 0 L 10 5 L 0 10 z" className={styles.projectedMarker} />
                                        </marker>
                                    </defs>
                                    {correctionSpheros.map((sphero) => {
                                        const debug = sphero.correction_debug!;
                                        const [prevStartX, prevStartY] = debug.previous_vector.start;
                                        const [prevEndX, prevEndY] = debug.previous_vector.end;
                                        const [projectedStartX, projectedStartY] = debug.projected_vector.start;
                                        const [projectedEndX, projectedEndY] = debug.projected_vector.end;

                                        return (
                                            <g key={sphero.id}>
                                                <line
                                                    x1={prevStartX}
                                                    y1={prevStartY}
                                                    x2={prevEndX}
                                                    y2={prevEndY}
                                                    className={styles.previousVector}
                                                    markerEnd="url(#previous-vector-arrow)"
                                                />
                                                <line
                                                    x1={projectedStartX}
                                                    y1={projectedStartY}
                                                    x2={projectedEndX}
                                                    y2={projectedEndY}
                                                    className={styles.projectedVector}
                                                    markerEnd="url(#projected-vector-arrow)"
                                                />
                                                <foreignObject
                                                    x={Math.min(Math.max(projectedStartX, 0), gridWidth)}
                                                    y={Math.min(Math.max(projectedStartY, 0), gridHeight)}
                                                    width={gridWidth * 0.24}
                                                    height={gridHeight * 0.12}
                                                    className={styles.angleObject}
                                                >
                                                    <div className={styles.angleLabel}>
                                                        S{sphero.id} Δθ {formatAngle(debug.angle_change)}
                                                    </div>
                                                </foreignObject>
                                            </g>
                                        );
                                    })}
                                </svg>
                            )}
                        </div>

                        {/* Live indicator */}
                        <div className={`${styles.statusOverlay} ${styles.active}`}>
                            <FontAwesomeIcon icon={faCircle} className={styles.statusDot} />
                            LIVE
                        </div>
                    </>
                )}
            </div>

            {/* Stats sit under the feed, so they never cover the camera image */}
            {showStats && <div
                className={styles.statsBar}
                style={sizing === "aspect" ? barStyle : undefined}
            >
                <div className={styles.statCard}>
                    <p className={styles.statLabel}>FPS</p>
                    <p className={styles.statValue}>{serverStatus === "started" ? fps : 0}</p>
                </div>
                <div className={styles.statCard}>
                    <p className={styles.statLabel}>Frames</p>
                    <p className={styles.statValue}>{frameCount}</p>
                </div>
                <div className={styles.statCard}>
                    <p className={styles.statLabel}>Resolution</p>
                    <p className={styles.statValue}>{resolution ?? "—"}</p>
                </div>
            </div>}
        </div>
    );
}
