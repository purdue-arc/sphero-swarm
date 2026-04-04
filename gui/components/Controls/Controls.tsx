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
}: {
    constants: SpheroConstants;
    spheros: SpheroStatus[];
    setSpheros: any;
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

    const handleRehome = () => {
        sendControlCommand({ type: "rehome" });
    };

    const handleDisconnect = (id: string) => {
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
                    startConnectionDemo={startConnectionDemo}
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