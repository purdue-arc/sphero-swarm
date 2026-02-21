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
    const { connectState, startConnection, connectedCount, pendingCount, failedCount } = useSpheroConnection(spheros, setSpheros);

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
                    connectedCount={connectedCount}
                    pendingCount={pendingCount}
                    failedCount={failedCount}
                />
            </div>
            <div className={styles.spheroSection}>
                <SpheroConnectionList spheros={spheros} />
            </div>
        </>
    )
}