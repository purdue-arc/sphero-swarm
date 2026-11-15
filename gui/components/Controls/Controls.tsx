import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faRobot } from "@fortawesome/free-solid-svg-icons";
import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { SpheroConnectionStats } from "../SpheroConnection/SpheroConnectionStats";
import { SpheroConnectionList } from "../SpheroConnection/SpheroConnectionList";
import type { CoordinatorPi, SpheroConstants, SpheroStatus } from "../../types/swarm_types";
import styles from "./controls.module.css";

type ConnectState = "idle" | "connecting" | "connected" | "failed";
type PiStatus = { online?: boolean; state?: string; robots?: Array<{ robot_id: string; status: string; connected: boolean; error?: string | null }> };
type FleetStatus = { pis: Record<string, PiStatus> };
const coordinatorError = (error: unknown) =>
    `Coordinator unavailable: ${String(error)}. Check coordinator/minipc.json and authenticate SSH in the GUI launch terminal if prompted.`;

export function Controls({
    constants,
    spheros,
    setSpheros,
    beforeConnect,
    tableView = false,
}: {
    constants: SpheroConstants;
    spheros: SpheroStatus[];
    setSpheros: Dispatch<SetStateAction<SpheroStatus[]>>;
    algorithmRunning?: boolean;
    onAlgorithmStopped?: () => void;
    beforeConnect?: () => Promise<void>;
    tableView?: boolean;
}) {
    const [connectState, setConnectState] = useState<ConnectState>("idle");
    const [pis, setPis] = useState<CoordinatorPi[]>([]);
    const [piStatus, setPiStatus] = useState<FleetStatus | null>(null);
    const [message, setMessage] = useState("");

    const connectedCount = spheros.filter(ball => ball.connection === "connected").length;
    const pendingCount = spheros.filter(ball => ball.connection === "pending" || ball.connection === "found").length;
    const failedCount = spheros.filter(ball => ball.connection === "failed").length;

    const refreshFleet = useCallback(async () => {
        const piData = await window.electronAPI.coordinatorRequest<{ pis: CoordinatorPi[] }>("/api/pis");
        const statusData = await window.electronAPI.coordinatorRequest<FleetStatus>("/api/status");
        setPis(piData.pis || []);
        setPiStatus(statusData);

        const robots = Object.entries(statusData.pis || {}).flatMap(([pi, status]) =>
            (status.robots || []).map(robot => ({ ...robot, piNumber: Number(pi) })));
        setSpheros(previous => previous.map(ball => {
            const found = robots.find(robot => robot.robot_id === ball.id);
            if (!found) return { ...ball, connection: "not-attempted", piNumber: undefined };
            const isConnected = found.status === "connected" && found.connected;
            const isFailed = found.status === "failed" || found.status === "error";
            const isReleased = found.status === "released" || found.status === "idle";
            return {
                ...ball,
                connection: isConnected ? "connected" : isFailed ? "failed" : isReleased ? "not-attempted" : "pending",
                foundAt: isConnected ? (ball.foundAt ?? Date.now()) : ball.foundAt,
                piNumber: isReleased ? undefined : found.piNumber,
            };
        }));
        return statusData;
    }, [setSpheros]);

    useEffect(() => {
        void refreshFleet().catch(error => setMessage(coordinatorError(error)));
    }, [refreshFleet]);

    useEffect(() => {
        if (connectState === "connecting") return;
        const timer = window.setInterval(() => {
            void refreshFleet().catch(error => setMessage(coordinatorError(error)));
        }, 5000);
        return () => window.clearInterval(timer);
    }, [connectState, refreshFleet]);

    const startConnection = async () => {
        if (connectState === "connecting") return;
        setConnectState("connecting");
        setMessage("Finding online Pis...");
        setSpheros(previous => previous.map(ball => ({ ...ball, connection: "pending", piNumber: undefined, foundAt: undefined, batteryPercent: undefined })));
        try {
            await beforeConnect?.();
            const piData = await window.electronAPI.coordinatorRequest<{ pis: CoordinatorPi[] }>("/api/pis?refresh=1");
            const online = (piData.pis || []).filter(pi => pi.online);
            setPis(piData.pis || []);
            if (!online.length) throw new Error("No online Pis were found. Check the Pi network and coordinator.");
            await window.electronAPI.coordinatorRequest("/api/pis/select", "POST", { numbers: online.map(pi => pi.number) });

            setMessage(`Scanning ${online.length} Pi${online.length === 1 ? "" : "s"} for Spheros...`);
            const scan = await window.electronAPI.coordinatorRequest<{ robots: Array<{ robot_id: string }>; errors: Record<string, string> }>(
                "/api/scan", "POST", { seconds: 8 });
            const robotIds = constants.SPHERO_TAGS;
            if (!robotIds.length) throw new Error("No Sphero IDs are configured.");

            setMessage("Choosing the strongest Pi for each Sphero...");
            const auto = await window.electronAPI.coordinatorRequest<{ assignment: Record<string, string[]> }>(
                "/api/assign/auto", "POST", { mode: "signal", robots: robotIds });
            const assignment = auto.assignment || {};
            const ownerByRobot = new Map<string, number>();
            for (const [pi, ids] of Object.entries(assignment)) for (const id of ids) ownerByRobot.set(id, Number(pi));
            setSpheros(previous => previous.map(ball => ({
                ...ball,
                connection: "pending",
                piNumber: ownerByRobot.get(ball.id),
                foundAt: scan.robots.some(robot => robot.robot_id === ball.id) ? Date.now() : undefined,
            })));

            setMessage("Connecting Spheros through their assigned Pis...");
            const result = await window.electronAPI.coordinatorRequest<{ per_pi: Record<string, { ok?: boolean; error?: string }> }>(
                "/api/connect", "POST", { assignment });
            const connectErrors = Object.entries(result.per_pi || {}).filter(([, value]) => value?.ok === false)
                .map(([pi, value]) => `Pi ${pi}: ${value.error || "connection request failed"}`);
            if (connectErrors.length) setMessage(connectErrors.join("; "));

            const deadline = Date.now() + Math.max(90_000, robotIds.length * 35_000);
            let status: FleetStatus | null = null;
            while (Date.now() < deadline) {
                await new Promise(resolve => window.setTimeout(resolve, 2500));
                status = await window.electronAPI.coordinatorRequest<FleetStatus>("/api/status");
                const rows = Object.entries(status.pis || {}).flatMap(([pi, value]) =>
                    (value.robots || []).map(robot => ({ ...robot, pi: Number(pi) })));
                const allSettled = robotIds.every(id => {
                    const robot = rows.find(item => item.robot_id === id);
                    return robot && (robot.status === "connected" || robot.status === "failed" || robot.status === "error");
                });
                setPiStatus(status);
                setSpheros(previous => previous.map(ball => {
                    const robot = rows.find(item => item.robot_id === ball.id);
                    if (!robot) return ball;
                    const connected = robot.connected && robot.status === "connected";
                    return {
                        ...ball,
                        connection: connected ? "connected" : robot.status === "failed" || robot.status === "error" ? "failed" : "pending",
                        piNumber: robot.pi,
                        foundAt: connected ? (ball.foundAt ?? Date.now()) : ball.foundAt,
                    };
                }));
                if (allSettled) break;
            }
            const finalStatus = status || await refreshFleet();
            const finalRows = Object.values(finalStatus.pis || {}).flatMap(value => value.robots || []);
            const succeeded = robotIds.filter(id => finalRows.some(robot => robot.robot_id === id && robot.connected)).length;
            setConnectState(succeeded === robotIds.length ? "connected" : "failed");
            setMessage(`${succeeded} of ${robotIds.length} Spheros connected.`);
        } catch (error) {
            setConnectState("failed");
            setMessage(String(error));
            await refreshFleet().catch(() => undefined);
        }
    };

    const disconnectAll = async () => {
        setConnectState("connecting");
        setMessage("Disconnecting Spheros from the Pis...");
        try {
            await window.electronAPI.coordinatorRequest("/api/release", "POST", {});
            setSpheros(previous => previous.map(ball => ({
                ...ball, connection: "not-attempted", piNumber: undefined, foundAt: undefined,
            })));
            setConnectState("idle");
            setMessage("All Spheros disconnected.");
            await refreshFleet();
        } catch (error) {
            setConnectState("failed");
            setMessage(String(error));
            await refreshFleet().catch(() => undefined);
        }
    };

    const disconnectOne = async (robotId: string) => {
        setConnectState("connecting");
        setMessage(`Disconnecting ${robotId}...`);
        try {
            await window.electronAPI.coordinatorRequest("/api/release", "POST", { robots: [robotId] });
            setSpheros(previous => previous.map(ball => ball.id === robotId
                ? { ...ball, connection: "not-attempted", piNumber: undefined, foundAt: undefined }
                : ball));
            setConnectState("idle");
            setMessage(`${robotId} disconnected.`);
            await refreshFleet();
        } catch (error) {
            setConnectState("failed");
            setMessage(String(error));
            await refreshFleet().catch(() => undefined);
        }
    };

    const displayPis: CoordinatorPi[] = pis.length ? pis : Object.keys(piStatus?.pis || {}).map(number => ({
        number: Number(number), ip: null, online: Boolean(piStatus?.pis[number]?.online),
    }));

    return <div className={tableView ? styles.controlsLayout : undefined}>
        <section className={styles.spheroSection}>
            <div className={styles.sectionHeader}>
                <h2 className={styles.sectionTitle}>
                    <FontAwesomeIcon icon={faRobot} className={styles.sectionIcon} />
                    <span>{tableView ? "Controls" : "Sphero Fleet"}</span>
                </h2>
            </div>
            <SpheroConnectionStats connectState={connectState} startConnection={startConnection}
                startConnectionDemo={startConnection} connectedCount={connectedCount}
                pendingCount={pendingCount} failedCount={failedCount} />
            <button className={styles.rehomeButton} onClick={() => void disconnectAll()}
                disabled={connectState === "connecting" || connectedCount === 0}>
                Disconnect All
            </button>
            {message && <p className={styles.connectionMessage} role="status">{message}</p>}
        </section>

        {!tableView && <section className={styles.spheroSection}>
            <div className={styles.sectionHeader}><h2 className={styles.sectionTitle}><span>Pi Connections</span></h2></div>
            <div className={styles.piGrid}>
                {displayPis.map(pi => {
                    const live = piStatus?.pis?.[String(pi.number)];
                    const connected = live?.robots?.filter(robot => robot.connected && robot.status === "connected") || [];
                    return <article className={styles.piCard} key={pi.number}>
                        <div className={styles.piHeader}>
                            <strong>Pi {pi.number}</strong>
                            <span className={`${styles.piState} ${pi.online ? styles.piOnline : styles.piOffline}`}>
                                {pi.online ? "Online" : "Offline"}
                            </span>
                        </div>
                        <div className={styles.piAddress}>{pi.hostname || pi.ip || "Address unavailable"}</div>
                        <div className={styles.piRobotsLabel}>Connected Spheros</div>
                        {connected.length
                            ? <ul className={styles.piRobotList}>{connected.map(robot => <li key={robot.robot_id}>{robot.robot_id}</li>)}</ul>
                            : <p className={styles.piEmpty}>{pi.online ? "No Spheros connected" : "Pi is offline"}</p>}
                    </article>;
                })}
                {!displayPis.length && <p className={styles.piEmpty}>Connect to the coordinator to discover Pis.</p>}
            </div>
        </section>}

        <section className={styles.spheroSection}>
            <div className={styles.sectionHeader}><h2 className={styles.sectionTitle}><span>{tableView ? "Connections" : "Sphero Status"}</span></h2></div>
            {tableView ? <div className={styles.spheroTableWrap}>
                <table className={styles.spheroTable}>
                    <thead><tr><th>ID</th><th>Sphero</th><th>Status</th><th>Found</th><th>Assigned Pi</th><th>Action</th></tr></thead>
                    <tbody>{spheros.map((ball, index) => <tr key={ball.id}>
                        <td className={styles.tableIndex}>{String(index + 1).padStart(2, "0")}</td>
                        <td className={styles.tableRobot}>{ball.id}</td>
                        <td><span className={`${styles.tableStatus} ${styles[`tableStatus_${ball.connection}`]}`}>
                            {ball.connection === "connected" ? "Connected" : ball.connection === "pending" ? "Scanning" : ball.connection === "found" ? "Found" : ball.connection === "failed" ? "Failed" : "Ready"}
                        </span></td>
                        <td>{ball.foundAt ? new Date(ball.foundAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" }) : "—"}</td>
                        <td>{ball.piNumber !== undefined ? `Pi ${ball.piNumber}` : "—"}</td>
                        <td>{ball.connection === "connected"
                            ? <button className={styles.tableAction} disabled={connectState === "connecting"} onClick={() => void disconnectOne(ball.id)}>Disconnect</button>
                            : ball.connection === "failed"
                                ? <button className={styles.tableAction} disabled={connectState === "connecting"} onClick={() => void startConnection()}>Retry Fleet</button>
                                : <span className={styles.tableDash}>—</span>}</td>
                    </tr>)}</tbody>
                </table>
            </div> : <SpheroConnectionList spheros={spheros} />}
        </section>
    </div>;
}
