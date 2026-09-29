import { useEffect, useRef, useState } from "react";
import type { SpheroStatus } from "../../types/swarm_types";

type ConnectState = "idle" | "connecting" | "connected" | "failed";

export function useSpheroConnection(
    spheros: SpheroStatus[],
    setSpheros: React.Dispatch<React.SetStateAction<SpheroStatus[]>>
) {
    const wsRef = useRef<WebSocket | null>(null);
    const statusRef = useRef(spheros);
    useEffect(() => { statusRef.current = spheros; }, [spheros]);
    const [connectState, setConnectState] = useState<ConnectState>(() =>
        spheros.some(s => s.connection !== "not-attempted") ? "connected" : "idle"
    );
    const timeoutRef = useRef<number | null>(null);
    const demoTimeoutsRef = useRef<number[]>([]);

    const cleanupSocket = () => {
        wsRef.current?.close();
        wsRef.current = null;
    };

    const cleanupDemoTimeouts = () => {
        demoTimeoutsRef.current.forEach((id) => clearTimeout(id));
        demoTimeoutsRef.current = [];
    };

    const connectedCount = spheros.filter((s) => s.connection === "connected").length;
    const pendingCount = spheros.filter((s) => s.connection === "pending" || s.connection === "found").length;
    const failedCount = spheros.filter((s) => s.connection === "failed").length;

    useEffect(() => () => {
        wsRef.current?.close();
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        demoTimeoutsRef.current.forEach(id => clearTimeout(id));
    }, []);

    const failConnection = () => {
        setSpheros((prev) =>
            prev.map((r) =>
                r.connection === "pending" || r.connection === "found" ? { ...r, connection: "failed" } : r
            )
        );

        setConnectState("failed");
        cleanupSocket();

        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
        }
    };

    const startConnectionDemo = () => {
        if (connectState === "connecting") return;

        setConnectState("connecting");
        cleanupDemoTimeouts();

        // Set all spheros to pending state
        setSpheros((prev) => prev.map((r) => ({ ...r, connection: "pending", foundAt: undefined, batteryPercent: undefined })));

        // For each sphero, schedule connection after random delay (0-4 seconds)
        spheros.forEach((sphero) => {
            const randomDelay = Math.random() * 4000; // 0-4 seconds
            console.log(`[Demo] Sphero ${sphero.id} will connect in ${randomDelay.toFixed(0)}ms`);
            
            const timeoutId = window.setTimeout(() => {
                setSpheros((prev) =>
                    prev.map((r) =>
                        r.id === sphero.id ? { ...r, connection: "connected", foundAt: Date.now() } : r
                    )
                );
            }, randomDelay);

            demoTimeoutsRef.current.push(timeoutId);
        });
    };

    const startConnection = () => {
        if (connectState === "connecting") return;

        setConnectState("connecting");
        timeoutRef.current = window.setTimeout(() => {
            console.warn("Connection timed out after 30s");
            failConnection();
        }, 30_000);

        setSpheros((prev) => prev.map((r) => ({ ...r, connection: "pending", foundAt: undefined, batteryPercent: undefined })));

        const ws = new WebSocket("ws://localhost:6768");
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("WebSocket opened for Sphero connection");
            ws.send(
                JSON.stringify({
                    type: "connect",
                    spheros: spheros.map((r) => r.id),
                })
            );
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("Received Sphero message:", data);

            switch (data.type) {
                case "ball_found":
                    setSpheros((prev) => prev.map((r) =>
                        r.id === data.ball && r.connection !== "connected"
                            ? { ...r, connection: "found", foundAt: typeof data.found_at === "number" ? data.found_at * 1000 : Date.now() }
                            : r
                    ));
                    break;
                case "ball_connected":
                    setSpheros((prev) =>
                        prev.map((r) =>
                            r.id === data.ball.split(" ")[0]
                                ? { ...r, connection: "connected", foundAt: r.foundAt ?? Date.now(), batteryPercent: typeof data.battery_percent === "number" ? data.battery_percent : undefined }
                                : r
                        )
                    );
                    break;

                case "ball_failed":
                    setSpheros((prev) =>
                        prev.map((r) =>
                            r.id === data.ball.split(" ")[0]
                                ? { ...r, connection: "failed" }
                                : r
                        )
                    );
                    break;

                case "session_ready":
                    if (timeoutRef.current) {
                        clearTimeout(timeoutRef.current);
                    }
                    // Individual connection events may still be queued after this marker.
                    timeoutRef.current = window.setTimeout(() => {
                        setSpheros(prev => prev.map(ball => ball.connection === "pending" || ball.connection === "found" ? { ...ball, connection: "failed" } : ball));
                        setConnectState(statusRef.current.some(ball => ball.connection !== "connected") ? "failed" : "connected");
                        cleanupSocket();
                        timeoutRef.current = null;
                    }, 800);
                    break;

                case "scan_failed":
                    // A partial scan can still connect the balls that were found.
                    break;
            }
        };

        ws.onerror = () => {
            console.error("WebSocket error during Sphero connection");
            failConnection();
        };

        ws.onclose = () => {
            console.log("WebSocket closed");
        };
    };

    const retryConnection = (id: string) => {
        setSpheros(prev => prev.map(s => s.id === id ? { ...s, connection: "pending", batteryPercent: undefined } : s));
        const ws = new WebSocket("ws://localhost:6768");
        const timer = window.setTimeout(() => {
            ws.close();
            setSpheros(prev => prev.map(s => s.id === id && (s.connection === "pending" || s.connection === "found") ? { ...s, connection: "failed" } : s));
        }, 30000);
        ws.onopen = () => ws.send(JSON.stringify({ type: "retry", ball: id }));
        ws.onmessage = event => {
            const data = JSON.parse(event.data);
            if (data.type === "ball_found" && data.ball === id) {
                setSpheros(prev => prev.map(s => s.id === id ? { ...s, connection: "found", foundAt: typeof data.found_at === "number" ? data.found_at * 1000 : Date.now() } : s));
                return;
            }
            if (data.type !== "ball_connected" && data.type !== "ball_failed") return;
            clearTimeout(timer);
            setSpheros(prev => prev.map(s => s.id === id ? { ...s, connection: data.type === "ball_connected" ? "connected" : "failed", foundAt: s.foundAt ?? (data.type === "ball_connected" ? Date.now() : undefined), batteryPercent: data.type === "ball_connected" && typeof data.battery_percent === "number" ? data.battery_percent : undefined } : s));
            ws.close();
        };
        ws.onerror = () => {
            clearTimeout(timer);
            setSpheros(prev => prev.map(s => s.id === id ? { ...s, connection: "failed" } : s));
            ws.close();
        };
    };

    const resetConnection = () => {
        cleanupSocket();
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        cleanupDemoTimeouts();
        setConnectState("idle");
        setSpheros(prev => prev.map(s => ({ ...s, connection: "not-attempted", foundAt: undefined, batteryPercent: undefined })));
    };

    const getButtonConfig = () => {
        switch (connectState) {
            case "idle":
                return {
                    label: "Connect All Spheros",
                    icon: "faPlay",
                    disabled: false,
                };
            case "connecting":
                return {
                    label: "Connecting...",
                    icon: "faSpinner",
                    disabled: true,
                };
            case "connected":
                return {
                    label: "All Connected",
                    icon: "faCheck",
                    disabled: true,
                };
            case "failed":
                return {
                    label: "Retry Connection",
                    icon: "faRotateRight",
                    disabled: false,
                };
        }
    };

    return {
        connectState,
        startConnection,
        retryConnection,
        resetConnection,
        startConnectionDemo,
        getButtonConfig,
        connectedCount,
        pendingCount,
        failedCount,
    };
}
