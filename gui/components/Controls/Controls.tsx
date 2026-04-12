import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    faRobot,
} from "@fortawesome/free-solid-svg-icons";
import { SpheroConnectionStats } from "../SpheroConnection/SpheroConnectionStats";
import { SpheroConnectionList } from "../SpheroConnection/SpheroConnectionList";
import { useSpheroConnection } from "../SpheroConnection/useSpheroConnection";
import type { SpheroConstants, SpheroStatus } from "../../types/swarm_types";

import styles from "./controls.module.css"

export function Controls({
    constants,
    spheros,
    setSpheros,
    algorithmRunning = false,
}: {
    constants: SpheroConstants;
    spheros: SpheroStatus[];
    setSpheros: any;
    algorithmRunning?: boolean;
}) {
    const { connectState, startConnection, startConnectionDemo, connectedCount, pendingCount, failedCount } = useSpheroConnection(spheros, setSpheros);

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
        setSpheros(prev => prev.map(s => s.id === id ? { ...s, connection: "not-attempted" } : s));
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
                    startConnection={startConnection}
                    startConnectionDemo={startConnection}
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
            </div>
            <div className={styles.spheroSection}>
                <SpheroConnectionList spheros={spheros} onDisconnect={handleDisconnect} />
            </div>
        </>
    )
}