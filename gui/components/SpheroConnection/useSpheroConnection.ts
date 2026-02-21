import { useRef, useState } from "react";
import type { SpheroStatus } from "../../types/swarm_types";

type ConnectState = "idle" | "connecting" | "connected" | "failed";

export function useSpheroConnection(
    spheros: SpheroStatus[],
    setSpheros: React.Dispatch<React.SetStateAction<SpheroStatus[]>>
) {
    const wsRef = useRef<WebSocket | null>(null);
    const [connectState, setConnectState] = useState<ConnectState>("idle");
    const timeoutRef = useRef<number | null>(null);

    const cleanupSocket = () => {
        wsRef.current?.close();
        wsRef.current = null;
    };

    const failConnection = () => {
        setSpheros((prev) =>
            prev.map((r) =>
                r.connection === "pending" ? { ...r, connection: "failed" } : r
            )
        );

        setConnectState("failed");
        cleanupSocket();

        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
        }
    };

    const startConnection = () => {
        if (connectState === "connecting") return;

        setConnectState("connecting");
        timeoutRef.current = window.setTimeout(() => {
            console.warn("Connection timed out after 30s");
            failConnection();
        }, 30_000);

        setSpheros((prev) => prev.map((r) => ({ ...r, connection: "pending" })));

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
                case "ball_connected":
                    setSpheros((prev) =>
                        prev.map((r) =>
                            r.id === data.ball.split(" ")[0]
                                ? { ...r, connection: "connected" }
                                : r
                        )
                    );
                    break;

                case "ball_failed":
                    setSpheros((prev) =>
                        prev.map((r) =>
                            r.id === data.ball
                                ? { ...r, connection: "failed" }
                                : r
                        )
                    );
                    break;

                case "session_ready":
                    if (timeoutRef.current) {
                        clearTimeout(timeoutRef.current);
                        timeoutRef.current = null;
                    }
                    setConnectState("connected");
                    cleanupSocket();
                    break;

                case "scan_failed":
                    failConnection();
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

    const connectedCount = spheros.filter((s) => s.connection === "connected").length;
    const pendingCount = spheros.filter((s) => s.connection === "pending").length;
    const failedCount = spheros.filter((s) => s.connection === "failed").length;

    return {
        connectState,
        startConnection,
        getButtonConfig,
        connectedCount,
        pendingCount,
        failedCount,
    };
}
