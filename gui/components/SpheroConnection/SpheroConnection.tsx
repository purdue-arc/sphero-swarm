import { useRef, useState } from "react";
import styles from "./SpheroConnection.module.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    faCircle,
    faPlay,
    faRotateRight,
    faSpinner,
    faCheck,
} from "@fortawesome/free-solid-svg-icons";
import type { SpheroStatus } from "../../types/swarm_types";

type ConnectState = "idle" | "connecting" | "connected" | "failed";

export function SpheroConnection({
    spheros,
    setSpheros,
}: {
    spheros: SpheroStatus[];
    setSpheros: React.Dispatch<React.SetStateAction<SpheroStatus[]>>;
}) {
    const wsRef = useRef<WebSocket | null>(null);
    const [connectState, setConnectState] = useState<ConnectState>("idle");
    const timeoutRef = useRef<number | null>(null);

    const cleanupSocket = () => {
        wsRef.current?.close();
        wsRef.current = null;
    };

    const failConnection = () => {
        setSpheros((prev) =>
            prev.map((r) =>
                r.connection === "pending" ? { ...r, connection: "failed" } : r
            )
        );

        setConnectState("failed");
        cleanupSocket();

        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
        }
    };

    const startConnection = () => {
        if (connectState === "connecting") return;

        setConnectState("connecting");
        timeoutRef.current = window.setTimeout(() => {
            console.warn("Connection timed out after 30s");
            failConnection();
        }, 30_000);

        setSpheros((prev) => prev.map((r) => ({ ...r, connection: "pending" })));

        const ws = new WebSocket("ws://localhost:6768");
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("WebSocket opened for Sphero connection");
            ws.send(
                JSON.stringify({
                    type: "connect",
                    spheros: spheros.map((r) => r.id),
                })
            );
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("Received Sphero message:", data);

            switch (data.type) {
                case "ball_connected":
                    setSpheros((prev) =>
                        prev.map((r) =>
                            r.id === data.ball.split(" ")[0]
                                ? { ...r, connection: "connected" }
                                : r
                        )
                    );
                    break;

                case "ball_failed":
                    setSpheros((prev) =>
                        prev.map((r) =>
                            r.id === data.ball
                                ? { ...r, connection: "failed" }
                                : r
                        )
                    );
                    break;

                case "session_ready":
                    if (timeoutRef.current) {
                        clearTimeout(timeoutRef.current);
                        timeoutRef.current = null;
                    }
                    setConnectState("connected");
                    cleanupSocket();
                    break;

                case "scan_failed":
                    failConnection();
                    break;
            }
        };

        ws.onerror = () => {
            console.error("WebSocket error during Sphero connection");
            failConnection();
        };

        ws.onclose = () => {
            console.log("WebSocket closed");
        };
    };

    const getButtonConfig = () => {
        switch (connectState) {
            case "idle":
                return {
                    label: "Connect All Spheros",
                    icon: faPlay,
                    disabled: false,
                };
            case "connecting":
                return {
                    label: "Connecting...",
                    icon: faSpinner,
                    disabled: true,
                };
            case "connected":
                return {
                    label: "All Connected",
                    icon: faCheck,
                    disabled: true,
                };
            case "failed":
                return {
                    label: "Retry Connection",
                    icon: faRotateRight,
                    disabled: false,
                };
        }
    };

    const buttonConfig = getButtonConfig();

    // Calculate summary stats
    const connectedCount = spheros.filter((s) => s.connection === "connected").length;
    const pendingCount = spheros.filter((s) => s.connection === "pending").length;
    const failedCount = spheros.filter((s) => s.connection === "failed").length;

    const getConnectionLabel = (connection: string) => {
        switch (connection) {
            case "connected":
                return "Connected";
            case "pending":
                return "Connecting";
            case "failed":
                return "Failed";
            default:
                return "Not Attempted";
        }
    };

    return (
        <div className={styles.spheroContainer}>
            {/* Summary Stats */}
            <div className={styles.summaryStats}>
                <div className={`${styles.summaryCard} ${styles.success}`}>
                    <p className={styles.summaryValue}>{connectedCount}</p>
                    <p className={styles.summaryLabel}>Connected</p>
                </div>
                <div className={`${styles.summaryCard} ${styles.pending}`}>
                    <p className={styles.summaryValue}>{pendingCount}</p>
                    <p className={styles.summaryLabel}>Pending</p>
                </div>
                <div className={`${styles.summaryCard} ${styles.error}`}>
                    <p className={styles.summaryValue}>{failedCount}</p>
                    <p className={styles.summaryLabel}>Failed</p>
                </div>
            </div>

            {/* Sphero Cards Grid */}
            <div className={styles.spheroGrid}>
                {spheros.map((sphero) => (
                    <div
                        key={sphero.id}
                        className={`${styles.spheroCard} ${styles[sphero.connection]}`}
                    >
                        <div className={styles.spheroHeader}>
                            <div className={styles.spheroIdContainer}>
                                <FontAwesomeIcon
                                    icon={faCircle}
                                    className={`${styles.connectionStatus} ${
                                        sphero.connection === "not-attempted"
                                            ? styles.notAttempted
                                            : styles[sphero.connection]
                                    }`}
                                />
                                <span className={styles.spheroId}>{sphero.id}</span>
                            </div>
                            <span
                                className={`${styles.connectionBadge} ${
                                    sphero.connection === "not-attempted"
                                        ? styles.notAttempted
                                        : styles[sphero.connection]
                                }`}
                            >
                                {getConnectionLabel(sphero.connection)}
                            </span>
                        </div>

                        <div className={styles.spheroPositions}>
                            <div className={styles.positionRow}>
                                <span className={styles.positionLabel}>Expected</span>
                                <span className={styles.positionValue}>
                                    {sphero.expectedPosition
                                        ? `(${sphero.expectedPosition[0]}, ${sphero.expectedPosition[1]})`
                                        : "N/A"}
                                </span>
                                <span className={styles.positionArrow}>→</span>
                                <span
                                    className={`${styles.positionValue} ${
                                        sphero.connection === "connected"
                                            ? styles.highlight
                                            : ""
                                    }`}
                                >
                                    {sphero.connection === "connected"
                                        ? `(${sphero.actualPosition[0]}, ${sphero.actualPosition[1]})`
                                        : "—"}
                                </span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Connection Control */}
            <div className={styles.connectionControls}>
                <button
                    className={`${styles.connectButton} ${styles[connectState]}`}
                    disabled={buttonConfig.disabled}
                    onClick={startConnection}
                >
                    <FontAwesomeIcon
                        icon={buttonConfig.icon}
                        className={`${styles.buttonIcon} ${
                            connectState === "connecting" ? styles.spinningIcon : ""
                        }`}
                    />
                    {buttonConfig.label}
                </button>
            </div>
        </div>
    );
}