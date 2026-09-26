import { useEffect, useState, useRef, type Dispatch, type SetStateAction } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCircle, faVideoSlash } from "@fortawesome/free-solid-svg-icons";
import styles from "./streamViewer.module.css";
import type { SimulationSnapshot } from "../../types/swarm_types";

type StreamStatus = "stopped" | "starting" | "started";

function formatAngle(angle: number) {
    const rounded = Math.round(angle);
    return `${rounded > 0 ? "+" : ""}${rounded}°`;
}

export function StreamViewer({
    port,
    serverStatus,
    setServerStatus,
    latestSimulationSnapshot,
    showCorrectionVectors = false,
}: {
    port: number;
    serverStatus: StreamStatus;
    setServerStatus: Dispatch<SetStateAction<StreamStatus>>;
    latestSimulationSnapshot?: SimulationSnapshot | null;
    showCorrectionVectors?: boolean;
}) {
    const [imageSrc, setImageSrc] = useState<string>("");
    const [frameCount, setFrameCount] = useState<number>(0);
    const [fps, setFps] = useState<number>(0);
    
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<any>(null);
    const shouldConnectRef = useRef<boolean>(false);
    const fpsIntervalRef = useRef<any>(null);
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
            setFps(0);
            frameCountRef.current = 0;
        }

        return () => {
            if (fpsIntervalRef.current) {
                clearInterval(fpsIntervalRef.current);
            }
        };
    }, [serverStatus]);

    useEffect(() => {
        shouldConnectRef.current = serverStatus !== "stopped";

        if (serverStatus === "stopped") {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
            }

            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }

            setImageSrc("");
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
    }, [serverStatus, port]);

    useEffect(() => {
        // Avoid reviving the stream state from late frames after a stop request.
        if (imageSrc !== "" && shouldConnectRef.current && serverStatus !== "stopped") {
            setServerStatus("started");
        }
    }, [imageSrc, serverStatus, setServerStatus]);

    const correctionSpheros = latestSimulationSnapshot?.spheros.filter(
        sphero => sphero.correction_debug !== undefined && sphero.correction_debug !== null
    ) ?? [];
    const gridWidth = Math.max(1, (latestSimulationSnapshot?.grid.width ?? 2) - 1);
    const gridHeight = Math.max(1, (latestSimulationSnapshot?.grid.height ?? 2) - 1);
    const shouldShowCorrections = showCorrectionVectors && correctionSpheros.length > 0;

    return (
        <div
            className={`${styles.imageViewer} ${
                serverStatus !== "stopped" ? styles.active : ""
            }`}
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
                        <img src={imageSrc} alt="Camera feed" />
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

                    {/* Stats overlay */}
                    <div className={styles.statsOverlay}>
                        <div className={styles.statCard}>
                            <p className={styles.statLabel}>FPS</p>
                            <p className={styles.statValue}>{fps}</p>
                        </div>
                        <div className={styles.statCard}>
                            <p className={styles.statLabel}>Frames</p>
                            <p className={styles.statValue}>{frameCount}</p>
                        </div>
                        <div className={styles.statCard}>
                            <p className={styles.statLabel}>Resolution</p>
                            <p className={styles.statValue}>1080p</p>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
