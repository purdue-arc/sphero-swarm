import { useState } from "react";
import styles from "./runner.module.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPlay, faStop, faCircle } from "@fortawesome/free-solid-svg-icons";

interface RobotStatus {
    id: string;
    connected: boolean;
    expectedPosition: { x: number; y: number };
    actualPosition: { x: number; y: number };
}

export function Runner() {
    const [isServerRunning, setIsServerRunning] = useState(false);
    const [cameraImage, setCameraImage] = useState<string | null>(null);
    const [trackingImage, setTrackingImage] = useState<string | null>(null);

    // Mock data for robot statuses
    const [robots] = useState<RobotStatus[]>([
        { id: "ROB-001", connected: true, expectedPosition: { x: 150, y: 200 }, actualPosition: { x: 148, y: 202 } },
        { id: "ROB-002", connected: true, expectedPosition: { x: 300, y: 450 }, actualPosition: { x: 301, y: 449 } },
        { id: "ROB-003", connected: false, expectedPosition: { x: 500, y: 300 }, actualPosition: { x: 0, y: 0 } },
        { id: "ROB-004", connected: true, expectedPosition: { x: 250, y: 150 }, actualPosition: { x: 252, y: 151 } },
    ]);

    const handleStartServer = () => {
        setIsServerRunning(true);
    };

    const handleStopServer = () => {
        setIsServerRunning(false);
    };

    return (
        <div className={styles.container}>
            {/* Top Section - Camera Output */}
            <section className={styles.topSection}>
                <div className={styles.sectionHeader}>
                    <h2 className={styles.sectionTitle}>Camera Output</h2>
                    <div className={styles.serverStatus}>
                        <FontAwesomeIcon 
                            icon={faCircle} 
                            className={`${styles.statusIndicator} ${isServerRunning ? styles.running : styles.stopped}`}
                        />
                        <span className={styles.statusText}>
                            {isServerRunning ? "Server Running" : "Server Stopped"}
                        </span>
                    </div>
                </div>

                <div className={styles.imageViewer}>
                    {cameraImage ? (
                        <img src={cameraImage} alt="Camera feed" className={styles.image} />
                    ) : (
                        <div className={styles.imagePlaceholder}>
                            <p className={styles.placeholderText}>No camera feed available</p>
                        </div>
                    )}
                </div>

                <div className={styles.controls}>
                    <button 
                        className={`${styles.controlButton} ${styles.startButton}`}
                        onClick={handleStartServer}
                        disabled={isServerRunning}
                    >
                        <FontAwesomeIcon icon={faPlay} className={styles.buttonIcon} />
                        Start Server
                    </button>
                    <button 
                        className={`${styles.controlButton} ${styles.stopButton}`}
                        onClick={handleStopServer}
                        disabled={!isServerRunning}
                    >
                        <FontAwesomeIcon icon={faStop} className={styles.buttonIcon} />
                        Stop Server
                    </button>
                </div>
            </section>

            {/* Bottom Section - Robot Tracking */}
            <section className={styles.bottomSection}>
                <div className={styles.robotList}>
                    <h3 className={styles.subsectionTitle}>Robot Status</h3>
                    <div className={styles.robotItems}>
                        {robots.map((robot) => (
                            <div key={robot.id} className={styles.robotItem}>
                                <div className={styles.robotHeader}>
                                    <FontAwesomeIcon 
                                        icon={faCircle} 
                                        className={`${styles.connectionIndicator} ${robot.connected ? styles.connected : styles.disconnected}`}
                                    />
                                    <span className={styles.robotId}>{robot.id}</span>
                                    <span className={styles.positionValue}>
                                        {robot.connected 
                                            ? `(${robot.actualPosition.x}, ${robot.actualPosition.y})`
                                            : "N/A"
                                        }
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className={styles.trackingViewer}>
                    <h3 className={styles.subsectionTitle}>Position Tracking</h3>
                    <div className={styles.imageViewer}>
                        {trackingImage ? (
                            <img src={trackingImage} alt="Position tracking" className={styles.image} />
                        ) : (
                            <div className={styles.imagePlaceholder}>
                                <p className={styles.placeholderText}>No tracking data available</p>
                            </div>
                        )}
                    </div>
                </div>
            </section>
        </div>
    );
}