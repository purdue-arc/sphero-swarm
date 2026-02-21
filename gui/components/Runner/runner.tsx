import { useEffect, useState } from "react";
import styles from "./runner.module.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    faPlay,
    faStop,
    faCircle,
    faVideo,
    faRobot,
    faBrain,
    faGear,
    faEye,
    faChartLine,
    faCog,
    faPlug,
    faRotateRight
} from "@fortawesome/free-solid-svg-icons";
import { SpheroConnection } from "../SpheroConnection/SpheroConnection";
import { StreamViewer } from "../StreamViewer/streamViewer";
import type { SpheroConstants, SpheroStatus } from "../../types/swarm_types";

export function Runner({
    constants,
    spheros,
    setSpheros,
}: {
    constants: SpheroConstants;
    spheros: SpheroStatus[];
    setSpheros: any;
}) {
    const [perceptionRunning, setPerceptionRunning] = useState("stopped");
    const [controlsRunning, setControlsRunning] = useState("idle");
    const [algorithmsRunning, setAlgorithmsRunning] = useState("idle");

    const startSpotter = async () => {
        setPerceptionRunning("starting");
        await window.electronAPI.startSpheroSpotter();
    };

    const stopSpotter = async () => {
        setPerceptionRunning("stopped");
        await window.electronAPI.stopSpheroSpotter();
    };

    // Calculate system health
    const connectedSpheros = spheros.filter(s => s.connection === "connected").length;
    const totalSpheros = spheros.length;
    const systemHealth = perceptionRunning === "started" && connectedSpheros > 0 ? "operational" : 
                         perceptionRunning === "starting" ? "starting" :
                         "offline";

    return (
        <div className={styles.dashboard}>
            {/* Main Content Grid */}
            <div className={styles.mainGrid}>
                {/* Live Camera Feed */}
                <div className={styles.liveFeed}>
                    <div className={styles.sectionHeader}>
                        <h2 className={styles.sectionTitle}>
                            <FontAwesomeIcon icon={faVideo} className={styles.sectionIcon} />
                            Live Camera Feed
                        </h2>
                        <span className={`${styles.badge} ${styles[perceptionRunning]}`}>
                            <FontAwesomeIcon icon={faCircle} className={styles.badgeIcon} />
                            {perceptionRunning === "started" ? "Running" :
                             perceptionRunning === "starting" ? "Starting" :
                             "Stopped"}
                        </span>
                    </div>
                    <div className={styles.viewerContainer}>
                        <StreamViewer
                            port={6767}
                            serverStatus={perceptionRunning}
                            setServerStatus={setPerceptionRunning}
                        />
                    </div>
                </div>

                <div className={styles.controlsPanel}>
                    <div className={styles.controlCard}>
                        <h3 className={styles.cardTitle}>
                            <FontAwesomeIcon icon={faGear} className={styles.cardIcon} />
                            System Controls
                        </h3>
                        <div className={styles.buttonGroup}>
                            {perceptionRunning === "stopped" ? (
                                <button
                                    className={`${styles.button} ${styles.buttonPrimary}`}
                                    onClick={startSpotter}
                                >
                                    <FontAwesomeIcon icon={faPlay} className={styles.buttonIcon} />
                                    Start Perception
                                </button>
                            ) : (
                                <button
                                    className={`${styles.button} ${styles.buttonDanger}`}
                                    onClick={stopSpotter}
                                    disabled={perceptionRunning === "starting"}
                                >
                                    <FontAwesomeIcon icon={faStop} className={styles.buttonIcon} />
                                    Stop Perception
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            <div className={styles.spheroSection}>
                <div className={styles.sectionHeader}>
                    <h2 className={styles.sectionTitle}>
                        <FontAwesomeIcon icon={faRobot} className={styles.sectionIcon} />
                        Robot Fleet Status
                    </h2>
                </div>
                <SpheroConnection spheros={spheros} setSpheros={setSpheros} />
            </div>
        </div>
    );
}