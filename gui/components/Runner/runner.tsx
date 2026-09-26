import styles from "./runner.module.css";
import type { Dispatch, SetStateAction } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    faCircle,
    faVideo,
    faChartLine,
} from "@fortawesome/free-solid-svg-icons";
import { StreamViewer } from "../StreamViewer/streamViewer";
import { Simulation } from "../Simulation/simulation";
import type {
    SpheroConstants,
    SpheroStatus,
    SimulationSnapshot,
} from "../../types/swarm_types";

export function Runner({
    constants,
    spheros,
    perceptionStatus,
    setPerceptionStatus,
    latestSimulationSnapshot,
    onSimulationSnapshot,
    speed,
    onSpeedChange,
    useControls,
    onUseControlsChange,
    useAlgorithmColors,
    onUseAlgorithmColorsChange,
}: {
    constants: SpheroConstants;
    spheros: SpheroStatus[];
    perceptionStatus: "stopped" | "starting" | "started";
    setPerceptionStatus: Dispatch<SetStateAction<"stopped" | "starting" | "started">>;
    latestSimulationSnapshot: SimulationSnapshot | null;
    onSimulationSnapshot: (payload: SimulationSnapshot) => void;
    speed: number;
    onSpeedChange: (value: number) => void;
    useControls: boolean;
    onUseControlsChange: (value: boolean) => void;
    useAlgorithmColors: boolean;
    onUseAlgorithmColorsChange: (value: boolean) => void;
}) {
    const connectedSpheros = spheros.filter(s => s.connection === "connected").length;

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
                        <span className={`${styles.badge} ${styles[perceptionStatus]}`}>
                            <FontAwesomeIcon icon={faCircle} className={styles.badgeIcon} />
                            {perceptionStatus === "started" ? "Running" :
                             perceptionStatus === "starting" ? "Starting" :
                             "Stopped"}
                        </span>
                    </div>
                    <div className={styles.viewerContainer}>
                        <StreamViewer
                            port={6767}
                            serverStatus={perceptionStatus}
                            setServerStatus={setPerceptionStatus}
                            latestSimulationSnapshot={latestSimulationSnapshot}
                            showCorrectionVectors
                        />
                    </div>
                </div>

                <div className={styles.simulationPanel}>
                    <div className={styles.sectionHeader}>
                        <h2 className={styles.sectionTitle}>
                            <FontAwesomeIcon icon={faChartLine} className={styles.sectionIcon} />
                            Simulation Grid
                        </h2>
                        <span className={styles.simMeta}>{connectedSpheros} connected</span>
                    </div>
                    <div className={styles.simulationContainer}>
                        <Simulation
                            constants={constants}
                            compact
                            latestSnapshot={latestSimulationSnapshot}
                            onSnapshot={onSimulationSnapshot}
                            speed={speed}
                            onSpeedChange={onSpeedChange}
                            useControls={useControls}
                            onUseControlsChange={onUseControlsChange}
                            useAlgorithmColors={useAlgorithmColors}
                            onUseAlgorithmColorsChange={onUseAlgorithmColorsChange}
                        />
                    </div>
                </div>
            </div>

            
        </div>
    );
}
