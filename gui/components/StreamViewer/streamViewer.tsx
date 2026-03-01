import React, { useEffect, useState, useRef } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCircle, faVideo, faVideoSlash } from "@fortawesome/free-solid-svg-icons";
import styles from "./streamViewer.module.css";

export function StreamViewer({
    port,
    serverStatus,
    setServerStatus,
}: {
    port: number;
    serverStatus: string;
    setServerStatus: (status: string) => void;
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
        if (imageSrc !== "") {
            setServerStatus("started");
        }
    }, [imageSrc, setServerStatus]);

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
                    <img src={imageSrc} alt="Camera feed" />
                    
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