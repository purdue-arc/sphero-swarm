import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    faPlay,
    faRotateRight,
    faSpinner,
    faCheck,
} from "@fortawesome/free-solid-svg-icons";
import styles from "./SpheroConnection.module.css";

type ConnectState = "idle" | "connecting" | "connected" | "failed";

export function SpheroConnectionStats({
    connectState,
    startConnection,
    startConnectionDemo,
    connectedCount,
    pendingCount,
    failedCount,
}: {
    connectState: ConnectState;
    startConnection: () => void;
    startConnectionDemo: () => void;
    connectedCount: number;
    pendingCount: number;
    failedCount: number;
}) {
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

    return (
        <div className={styles.statsContainer}>
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

            {/* Connection Control */}
            <div className={styles.connectionControls}>
                <button
                    className={`${styles.connectButton} ${styles[connectState]}`}
                    disabled={buttonConfig.disabled}
                    onClick={startConnectionDemo}
                >
                    <FontAwesomeIcon
                        icon={buttonConfig.icon}
                        className={`${styles.buttonIcon} ${
                            connectState === "connecting" ? styles.spinningIcon : ""
                        }`}
                    />
                    {buttonConfig.label}
                </button>
                {/* <button
                    className={`${styles.connectButton} ${styles.demo}`}
                    disabled={connectState === "connecting"}
                    onClick={startConnectionDemo}
                    title="Demo: Connect spheres at random intervals"
                >
                    <FontAwesomeIcon icon={faPlay} className={styles.buttonIcon} />
                    Demo Connection
                </button> */}
            </div>
        </div>
    );
}
