import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCircle } from "@fortawesome/free-solid-svg-icons";
import type { SpheroStatus } from "../../types/swarm_types";
import styles from "./SpheroConnection.module.css";

export function SpheroConnectionList({
    spheros,
    onDisconnect,
}: {
    spheros: SpheroStatus[];
    onDisconnect?: (id: string) => void;
}) {
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
                                className={`${styles.connectionStatus} ${sphero.connection === "not-attempted"
                                        ? styles.notAttempted
                                        : styles[sphero.connection]
                                    }`}
                            />
                            <span className={styles.spheroId}>{sphero.id}</span>
                        </div>
                        <span
                            className={`${styles.connectionBadge} ${sphero.connection === "not-attempted"
                                    ? styles.notAttempted
                                    : styles[sphero.connection]
                                }`}
                        >
                            {getConnectionLabel(sphero.connection)}
                        </span>
                    </div>

                    <div className={styles.spheroPositions}>
                        <div className={styles.positionRow}>
                            <span className={styles.positionLabel}>Expected Position: </span>
                            <span className={styles.positionValue}>
                                {sphero.expectedPosition
                                    ? `(${sphero.expectedPosition[0]}, ${sphero.expectedPosition[1]})`
                                    : "N/A"}
                            </span>
                        </div>
                        <div className={styles.positionRow}>
                            <span className={styles.positionLabel}>Actual Position: </span>
                            <span
                                className={`${styles.positionValue} ${sphero.connection === "connected"
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
                    {onDisconnect && sphero.connection === "connected" && (
                        <button
                            className={styles.disconnectButton}
                            onClick={() => onDisconnect(sphero.id)}
                        >
                            Disconnect
                        </button>
                    )}
                </div>
            ))}
        </div>
    );
}
