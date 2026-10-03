import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    faRobot,
} from "@fortawesome/free-solid-svg-icons";
import { SpheroConnectionStats } from "../SpheroConnection/SpheroConnectionStats";
import { SpheroConnectionList } from "../SpheroConnection/SpheroConnectionList";
import { useSpheroConnection } from "../SpheroConnection/useSpheroConnection";
import type { SpheroConstants, SpheroStatus } from "../../types/swarm_types";
import { useState, type Dispatch, type SetStateAction } from "react";

import styles from "./controls.module.css"

export function Controls({
    spheros,
    setSpheros,
    algorithmRunning = false,
    onAlgorithmStopped,
}: {
    constants: SpheroConstants;
    spheros: SpheroStatus[];
    setSpheros: Dispatch<SetStateAction<SpheroStatus[]>>;
    algorithmRunning?: boolean;
    onAlgorithmStopped?: () => void;
}) {
    const { connectState, startConnection, retryConnection, resetConnection, connectedCount, pendingCount, failedCount } = useSpheroConnection(spheros, setSpheros);
    const [refreshState, setRefreshState] = useState<"idle" | "refreshing" | "started" | "failed">("idle");

    const handleConnect = async () => {
        setRefreshState("refreshing");
        try {
            const response = await window.electronAPI.startControls();
            if (response.status === "failed") throw new Error("Controls service failed to start");
            setRefreshState("started");
            startConnection();
        } catch {
            setRefreshState("failed");
        }
    };

    // helper that opens a short-lived socket to the control server and sends a JSON
    const sendControlCommand = (cmd: object) => {
        const ws = new WebSocket("ws://localhost:6768");
        ws.onopen = () => {
            ws.send(JSON.stringify(cmd));
            ws.close();
        };
    };

    // Helper to send reset command to algorithm server
    const sendAlgorithmReset = () => {
        const ws = new WebSocket("ws://localhost:6769");
        ws.onopen = () => {
            ws.send(JSON.stringify({ type: "reset" }));
            ws.close();
        };
    };

    const handleRehome = () => {
        // If algorithm is running, reset it first
        if (algorithmRunning) {
            console.log("[Controls] Algorithm running - sending reset before rehome");
            sendAlgorithmReset();
        }
        sendControlCommand({ type: "rehome" });
    };

    const handleDisconnect = (id: string) => {
        // If algorithm is running, reset it first
        if (algorithmRunning) {
            console.log("[Controls] Algorithm running - sending reset before disconnect");
            sendAlgorithmReset();
        }
        sendControlCommand({ type: "disconnect", ball: id });
        setSpheros(prev => prev.map(s => s.id === id ? { ...s, connection: "not-attempted", foundAt: undefined, batteryPercent: undefined } : s));
    };

    const handleDisconnectAll = async () => {
        setRefreshState("refreshing");
        try {
            if (algorithmRunning) {
                await window.electronAPI.restartAlgorithm();
                onAlgorithmStopped?.();
            }
            const response = await window.electronAPI.refreshControls();
            if (response.status !== "started") throw new Error("Controls restart failed");
            resetConnection();
            setRefreshState("started");
        } catch {
            setRefreshState("failed");
        }
    };

    const handleRefreshControls = async () => {
        setRefreshState("refreshing");
        try {
            if (algorithmRunning) {
                await window.electronAPI.restartAlgorithm();
                onAlgorithmStopped?.();
            }
            const response = await window.electronAPI.refreshControls();
            if (response?.status === "started") {
                resetConnection();
                setRefreshState("started");
                return;
            }
            setRefreshState("failed");
        } catch {
            setRefreshState("failed");
        }
    };

    return (
        <>
            <div className={styles.spheroSection}>
                <div className={styles.sectionHeader}>
                    <h2 className={styles.sectionTitle}>
                        <FontAwesomeIcon icon={faRobot} className={styles.sectionIcon} />
                        <span>Spheros Fleet Status</span>
                    </h2>
                </div>
                <SpheroConnectionStats
                    connectState={connectState}
                    startConnection={handleConnect}
                    startConnectionDemo={handleConnect}
                    connectedCount={connectedCount}
                    pendingCount={pendingCount}
                    failedCount={failedCount}
                />
                <button
                    className={styles.rehomeButton}
                    onClick={handleRehome}
                    disabled={connectedCount === 0}
                >
                    Re‑home All
                </button>
                <button className={styles.rehomeButton} onClick={handleDisconnectAll} disabled={connectedCount === 0 || refreshState === "refreshing"}>
                    Disconnect All
                </button>
                <div className={styles.controlsServerRow}>
                    <button
                        className={styles.refreshButton}
                        onClick={handleRefreshControls}
                        disabled={refreshState === "refreshing"}
                    >
                        {refreshState === "refreshing" ? "Restarting..." : "Restart Controls Service"}
                    </button>
                    <span
                        className={`${styles.serverLight} ${refreshState === "started" ? styles.serverLightGreen : ""}`}
                        aria-label="Controls script refresh status"
                        title={refreshState === "started" ? "Controls script running" : "Controls script not confirmed"}
                    />
                </div>
            </div>
            <div className={styles.spheroSection}>
                <SpheroConnectionList spheros={spheros} onDisconnect={handleDisconnect} onRetry={retryConnection} />
            </div>
        </>
    )
}
