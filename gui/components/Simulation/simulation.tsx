import { useEffect, useRef, useState, useCallback } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPlay, faPause } from "@fortawesome/free-solid-svg-icons";
import styles from "./simulation.module.css";
import type { SpheroConstants } from "../../types/swarm_types";

interface ServerSphero {
    id: number;       // 1-indexed
    x: number;
    y: number;
    color: string | [number, number, number];
    direction: number;
}

interface ServerPayload {
    timestamp: number;
    grid: { width: number; height: number };
    spheros: ServerSphero[];
    bonded_groups: number[][];  // arrays of 1-indexed ids
}

interface Ball {
    id: number;          // matches server id (1-indexed)
    color: string;
    glowColor: string;
    currentNode: number; // flat index = y * gridWidth + x
    targetNode: number;
    progress: number;    // 0..1
}

const GROUP_PALETTE: { color: string; glow: string }[] = [
    { color: "#a78bfa", glow: "rgba(167,139,250,0.7)" },
    { color: "#34d399", glow: "rgba(52,211,153,0.7)" },
    { color: "#f472b6", glow: "rgba(244,114,182,0.7)" },
    { color: "#60a5fa", glow: "rgba(96,165,250,0.7)" },
    { color: "#fbbf24", glow: "rgba(251,191,36,0.7)" },
    { color: "#f87171", glow: "rgba(248,113,113,0.7)" },
    { color: "#2dd4bf", glow: "rgba(45,212,191,0.7)" },
    { color: "#e879f9", glow: "rgba(232,121,249,0.7)" },
];

const WS_URL = "ws://localhost:6769";
const VIEW_SIZE = 500;
const PADDING = 40;
const NODE_RADIUS = 6;
const BALL_RADIUS = 8;
const MOVE_SPEED = 100; // pixels/sec

function toCssColor(input: string | [number, number, number] | undefined, fallback: string): string {
    if (typeof input === "string" && input.trim().length > 0) {
        return input;
    }
    if (Array.isArray(input) && input.length === 3) {
        const [r, g, b] = input;
        return `rgb(${r}, ${g}, ${b})`;
    }
    return fallback;
}

export function Simulation({constants} : {constants : SpheroConstants}) {
    const [gridSize, setGridSize] = useState({ width: constants.GRID_WIDTH, height: constants.GRID_HEIGHT });
    const [connected, setConnected] = useState(false);
    const [paused, setPaused] = useState(false);    
    const [running, setRunning] = useState(false);  
    const [currentEditPath, setEditPath] = useState<number[]>([]);
    const [editBall, setEditBall] = useState(false);
    const [selectedEditBallId, setSelectedEditBallId] = useState<number | null>(null);
    const [isPathDrawing, setIsPathDrawing] = useState(false);
    const [speed, setSpeed] = useState(4);                // current delay value
    const [useControls, setUseControls] = useState(false); // whether GUI commands are respected
    const [useAlgorithmColors, setUseAlgorithmColors] = useState(true); // true => match driver.py color behavior

    const ballsRef = useRef<Map<number, Ball>>(new Map());
    const groupColorRef = useRef<Map<number, number>>(new Map());
    const bondLinesRef = useRef<[number, number][]>([]);
    const prevPosMapRef = useRef<Map<number, { x: number; y: number }>>(new Map());
    const bondMoveCountRef = useRef<Map<string, number>>(new Map());

    const gridRef = useRef({ width: 10, height: 10 });

    const [, forceRender] = useState(0);
    const { width: COLS, height: ROWS } = gridSize;

    const wsRef = useRef<WebSocket | null>(null);
    const svgRef = useRef<SVGSVGElement | null>(null);

    const nodeIndex = useCallback((x: number, y: number, gw: number) => y * gw + x, []);

    const nodeCoords = useCallback((index: number, gw: number) => ({
        x: index % gw,
        y: Math.floor(index / gw),
    }), []);

    const sendCommand = useCallback((cmd: object) => {
        const ws = wsRef.current;
        if (ws && ws.readyState === WebSocket.OPEN) {
            console.log("sending: "+JSON.stringify(cmd))
            ws.send(JSON.stringify(cmd));
        }
    }, []);

    const getNodePos = useCallback((index: number, gw: number, gh: number) => {
        const xStep = (VIEW_SIZE - PADDING * 2) / (gw - 1);
        const yStep = (VIEW_SIZE - PADDING * 2) / (gh - 1);
        const col = index % gw;
        const row = Math.floor(index / gw);
        return { x: PADDING + col * xStep, y: PADDING + row * yStep };
    }, []);

    const getNodeFromPointer = useCallback((clientX: number, clientY: number) => {
        if (COLS <= 1 || ROWS <= 1) return null;
        const svg = svgRef.current;
        if (!svg) return null;

        const rect = svg.getBoundingClientRect();
        if (!rect.width || !rect.height) return null;

        const x = ((clientX - rect.left) / rect.width) * VIEW_SIZE;
        const y = ((clientY - rect.top) / rect.height) * VIEW_SIZE;

        const xStep = (VIEW_SIZE - PADDING * 2) / (COLS - 1);
        const yStep = (VIEW_SIZE - PADDING * 2) / (ROWS - 1);

        const col = Math.round((x - PADDING) / xStep);
        const row = Math.round((y - PADDING) / yStep);

        if (col < 0 || col >= COLS || row < 0 || row >= ROWS) return null;

        const idx = nodeIndex(col, row, COLS);
        const pos = getNodePos(idx, COLS, ROWS);
        const threshold = Math.max(12, Math.min(xStep, yStep) * 0.45);

        return Math.hypot(pos.x - x, pos.y - y) <= threshold ? idx : null;
    }, [COLS, ROWS, getNodePos, nodeIndex]);

    const appendPathNode = useCallback((idx: number) => {
        setEditPath(prev => {
            if (prev.length && prev[prev.length - 1] === idx) return prev;
            return [...prev, idx];
        });
    }, []);

    const handleSvgPointerDown = (evt: React.PointerEvent<SVGSVGElement>) => {
        if (!paused || !editBall || selectedEditBallId === null) return;
        const idx = getNodeFromPointer(evt.clientX, evt.clientY);
        if (idx === null) return;
        evt.preventDefault();
        evt.currentTarget.setPointerCapture(evt.pointerId);
        setIsPathDrawing(true);
        appendPathNode(idx);
    };

    const handleSvgPointerMove = (evt: React.PointerEvent<SVGSVGElement>) => {
        if (!isPathDrawing || !paused || !editBall || selectedEditBallId === null) return;
        const idx = getNodeFromPointer(evt.clientX, evt.clientY);
        if (idx === null) return;
        appendPathNode(idx);
    };

    const endPathDraw = (evt?: React.PointerEvent<SVGSVGElement>) => {
        if (evt && evt.currentTarget.hasPointerCapture(evt.pointerId)) {
            evt.currentTarget.releasePointerCapture(evt.pointerId);
        }
        setIsPathDrawing(false);
    };

    const handleBallPointerDown = (ball: Ball, evt: React.PointerEvent<SVGGElement>) => {
        if (!paused || !editBall) return;
        evt.preventDefault();
        evt.stopPropagation();

        setSelectedEditBallId(ball.id);
        setEditPath([ball.targetNode]);

        const idx = getNodeFromPointer(evt.clientX, evt.clientY);
        if (idx !== null && idx !== ball.targetNode) {
            setEditPath([ball.targetNode, idx]);
        }

        setIsPathDrawing(true);
    };

    // ── WebSocket ──────────────────────────────────────────────────────────

    useEffect(() => {
        let ws: WebSocket;
        let dead = false;

        function connect() {
            ws = new WebSocket(WS_URL);
            wsRef.current = ws;

            ws.onopen = () => { if (!dead) setConnected(true); };
            ws.onclose = () => {
                setConnected(false);
                if (!dead) setTimeout(connect, 1500);
            };
            ws.onerror = () => ws.close();

            ws.onmessage = (evt) => {
                let payload: ServerPayload;
                try { payload = JSON.parse(evt.data); } catch { return; }
                console.log(payload)

                const gw = payload.grid.width;
                const gh = payload.grid.height;
                gridRef.current = { width: gw, height: gh };
                setGridSize({ width: gw, height: gh });

                const newGroupColor = new Map<number, number>();
                payload.bonded_groups.forEach((group, groupIdx) => {
                    const paletteIdx = groupIdx % GROUP_PALETTE.length;
                    group.forEach(id => newGroupColor.set(id, paletteIdx));
                });
                groupColorRef.current = newGroupColor;

                const balls = ballsRef.current;
                const seenIds = new Set<number>();

                payload.spheros.forEach((s) => {
                    seenIds.add(s.id);
                    const target = nodeIndex(s.x, s.y, gw);
                    const paletteIdx = newGroupColor.get(s.id) ?? (s.id - 1) % GROUP_PALETTE.length;
                    const palette = GROUP_PALETTE[paletteIdx];
                    const spheroCssColor = toCssColor(s.color, palette.color);

                    if (balls.has(s.id)) {
                        const ball = balls.get(s.id)!;
                        // Only update target if the sphero actually moved
                        if (ball.targetNode !== target) {
                            ball.currentNode = ball.targetNode;
                            ball.targetNode = target;
                            ball.progress = 0;
                        }
                        // Always sync colour to algorithm/driver-provided sphero color.
                        ball.color = spheroCssColor;
                        ball.glowColor = spheroCssColor;
                    } else {
                        balls.set(s.id, {
                            id: s.id,
                            color: spheroCssColor,
                            glowColor: spheroCssColor,
                            currentNode: target,
                            targetNode: target,
                            progress: 1,
                        });
                    }
                });

                // Remove balls for spheros no longer in payload
                for (const id of balls.keys()) {
                    if (!seenIds.has(id)) balls.delete(id);
                }

                const posMap = new Map<number, { x: number; y: number }>();
                payload.spheros.forEach(s => posMap.set(s.id, { x: s.x, y: s.y }));

                const lines: [number, number][] = [];
                const seen = new Set<string>();

                // traverse groups to build bond lines, but only include bonds that
                // have been "activated" by moving together at least once
                payload.bonded_groups.forEach((group) => {
                    if (group.length < 2) return;
                    for (let i = 0; i < group.length; i++) {
                        for (let j = i + 1; j < group.length; j++) {
                            const a = group[i], b = group[j];
                            const pa = posMap.get(a), pb = posMap.get(b);
                            if (!pa || !pb) continue;
                            const dx = Math.abs(pa.x - pb.x);
                            const dy = Math.abs(pa.y - pb.y);
                            // Cardinal and diagonal neighbours
                            if ((dx === 1 && dy === 0) || (dx === 0 && dy === 1) || (dx === 1 && dy === 1)) {
                                const key = `${Math.min(a, b)}-${Math.max(a, b)}`;

                                // count joint moves for this bond
                                const prevA = prevPosMapRef.current.get(a);
                                const prevB = prevPosMapRef.current.get(b);
                                if (prevA && prevB) {
                                    const movedA = prevA.x !== pa.x || prevA.y !== pa.y;
                                    const movedB = prevB.x !== pb.x || prevB.y !== pb.y;
                                    if (movedA && movedB) {
                                        const prevCount = bondMoveCountRef.current.get(key) || 0;
                                        bondMoveCountRef.current.set(key, prevCount + 1);
                                    }
                                }

                                const count = bondMoveCountRef.current.get(key) || 0;
                                if (count > 1 && !seen.has(key)) {
                                    seen.add(key);
                                    lines.push([a, b]);
                                }
                            }
                        }
                    }
                });
                bondLinesRef.current = lines;

                // update previous positions for next tick
                prevPosMapRef.current = posMap;
            };
        }

        connect();
        return () => { dead = true; ws?.close(); };
    }, [nodeIndex]);

    // helper to toggle pause/resume on the server
    const togglePause = () => {
        if (!running) return;
        const ws = wsRef.current;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: paused ? "resume" : "pause" }));
        }
        setPaused(p => !p);
    };

    // ── Animation loop ─────────────────────────────────────────────────────

    useEffect(() => {
        let last = performance.now();
        let raf: number;

        const tick = (now: number) => {
            const dt = (now - last) / 1000;
            last = now;

            for (const ball of ballsRef.current.values()) {
                if (ball.progress >= 1) continue;
                const from = getNodePos(ball.currentNode, gridRef.current.width, gridRef.current.height);
                const to = getNodePos(ball.targetNode, gridRef.current.width, gridRef.current.height);
                const dx = to.x - from.x;
                const dy = to.y - from.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                const moveAmount = dt * MOVE_SPEED / distance;
                ball.progress = Math.min(1, ball.progress + moveAmount);
            }

            forceRender(v => v + 1);
            raf = requestAnimationFrame(tick);
        };

        raf = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(raf);
    }, [getNodePos]);

    // ── Derived render values ──────────────────────────────────────────────

    const balls = Array.from(ballsRef.current.values());

    function ballPos(ball: Ball) {
        const from = getNodePos(ball.currentNode, COLS, ROWS);
        const to = getNodePos(ball.targetNode, COLS, ROWS);
        const t = ball.progress;
        return { cx: from.x + (to.x - from.x) * t, cy: from.y + (to.y - from.y) * t };
    }

    const handleStart = () => {
        sendCommand({ type: "start" });
        sendCommand({ type: "speed", value: speed });
        setRunning(true);
        setPaused(false);
    };

    const handleStop = () => {
        sendCommand({ type: "reset" });
        setRunning(false);
        setPaused(false);
        setEditBall(false);
        setSelectedEditBallId(null);
        setEditPath([]);
        setIsPathDrawing(false);
        // clear animation state and bonds but keep speed slider value
        ballsRef.current.clear();
        bondLinesRef.current = [];
        groupColorRef.current.clear();
        prevPosMapRef.current.clear();
        bondMoveCountRef.current.clear();
    };

    const handleSpeedChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = parseFloat(e.target.value);
        setSpeed(val);
        sendCommand({ type: "speed", value: val });
    };

    const handleEditBall = () => {
        if (!paused) return;

        if (!editBall) {
            sendCommand({ type: "edit_ball" });
            setSelectedEditBallId(null);
            setEditPath([]);
            setIsPathDrawing(false);
        } else {
            const payloadPath = currentEditPath.map(idx => nodeCoords(idx, COLS));
            sendCommand({ type: "done_ball", ball_id: selectedEditBallId, path: payloadPath });
            setSelectedEditBallId(null);
            setEditPath([]);
            setIsPathDrawing(false);
        }

        setEditBall(prev => !prev);
    };

    const toggleUseControls = () => {
        const next = !useControls;
        setUseControls(next);
        sendCommand({ type: "use_controls", value: next });
        if (!next) {
            setRunning(false);
            setPaused(false);
            setEditBall(false);
            setSelectedEditBallId(null);
            setEditPath([]);
            setIsPathDrawing(false);
        }
    };

    const toggleUseAlgorithmColors = () => {
        const next = !useAlgorithmColors;
        setUseAlgorithmColors(next);
        sendCommand({ type: "use_algorithm_colors", value: next });
    };

    // ── Render ─────────────────────────────────────────────────────────────

    return (
        <div className={styles.simulationContainer}>
            {/* Grid canvas */}
            <div className={styles.gridWrapper}>
                {paused && (
                    <div className={styles.pausedBadge}>
                        <div className={styles.pausedDot} />
                        Paused
                    </div>
                )}
            <svg
                ref={svgRef}
                className={styles.gridSvg}
                width="100%"
                height="100%"
                viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`}
                onPointerDown={handleSvgPointerDown}
                onPointerMove={handleSvgPointerMove}
                onPointerUp={endPathDraw}
                onPointerLeave={endPathDraw}
            >
                <defs>
                    {balls.map(ball => (
                        <radialGradient key={ball.id} id={`grad-${ball.id}`} cx="40%" cy="35%" r="60%">
                            <stop offset="0%" stopColor="#fff" stopOpacity="0.9" />
                            <stop offset="40%" stopColor={ball.color} />
                            <stop offset="100%" stopColor={ball.color} stopOpacity="0.7" />
                        </radialGradient>
                    ))}
                    {balls.map(ball => (
                        <filter key={ball.id} id={`glow-${ball.id}`} x="-50%" y="-50%" width="200%" height="200%">
                            <feGaussianBlur stdDeviation="4" />
                            <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
                        </filter>
                    ))}
                    <filter id="node-glow" x="-100%" y="-100%" width="300%" height="300%">
                        <feGaussianBlur stdDeviation="3" />
                        <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
                    </filter>
                    <filter id="bond-glow" x="-50%" y="-50%" width="200%" height="200%">
                        <feGaussianBlur stdDeviation="2.5" />
                        <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
                    </filter>
                </defs>

                {Array.from({ length: ROWS }).map((_, r) =>
                    Array.from({ length: COLS }).map((_, c) => {
                        const i = r * COLS + c;
                        const from = getNodePos(i, COLS, ROWS);
                        return (
                            <g key={`edges-${i}`}>
                                {([[r, c + 1], [r + 1, c], [r + 1, c + 1], [r + 1, c - 1]] as [number, number][])
                                    .map(([rr, cc], idx) => {
                                        if (rr >= ROWS || cc < 0 || cc >= COLS) return null;
                                        const to = getNodePos(rr * COLS + cc, COLS, ROWS);
                                        return (
                                            <line key={idx}
                                                x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                                                className={styles.gridLine}
                                            />
                                        );
                                    })}
                            </g>
                        );
                    })
                )}

                {Array.from({ length: ROWS * COLS }).map((_, i) => {
                    const { x, y } = getNodePos(i, COLS, ROWS);
                    const inEditPath = currentEditPath.includes(i);
                    return (
                        <circle key={`node-${i}`} cx={x} cy={y} r={NODE_RADIUS}
                            className={`${styles.gridNode} ${inEditPath ? styles.gridNodePath : ""}`}
                            filter="url(#node-glow)" />
                    );
                })}

                {editBall && currentEditPath.length > 1 && (
                    <polyline
                        points={currentEditPath
                            .map(idx => {
                                const { x, y } = getNodePos(idx, COLS, ROWS);
                                return `${x},${y}`;
                            })
                            .join(" ")}
                        className={styles.editPathLine}
                    />
                )}

                {editBall && currentEditPath.map((idx, i) => {
                    const { x, y } = getNodePos(idx, COLS, ROWS);
                    return (
                        <circle
                            key={`edit-path-node-${idx}-${i}`}
                            cx={x}
                            cy={y}
                            r={i === 0 ? 5 : 4}
                            className={styles.editPathNode}
                        />
                    );
                })}

                {/* Balls */}
                {balls.map(ball => {
                    const { cx, cy } = ballPos(ball);
                    return (
                        <g
                            key={ball.id}
                            className={`${styles.ball} ${editBall && selectedEditBallId === ball.id ? styles.ballSelected : ""}`}
                            filter={`url(#glow-${ball.id})`}
                            onPointerDown={(evt) => handleBallPointerDown(ball, evt)}
                        >
                            {/* Outer glow halo */}
                            <circle cx={cx} cy={cy} r={BALL_RADIUS + 5}
                                fill={ball.glowColor} opacity={0.15} />
                            {/* Main ball */}
                            <circle cx={cx} cy={cy} r={BALL_RADIUS}
                                fill={`url(#grad-${ball.id})`} />
                            {/* Specular highlight */}
                            <circle cx={cx - BALL_RADIUS * 0.25} cy={cy - BALL_RADIUS * 0.28}
                                r={BALL_RADIUS * 0.32} fill="rgba(255,255,255,0.45)" />
                        </g>
                    );
                })}

                {bondLinesRef.current.map(([a, b]) => {
                    const ba = ballsRef.current.get(a);
                    const bb = ballsRef.current.get(b);
                    if (!ba || !bb) return null;
                    const pa = ballPos(ba);
                    const pb = ballPos(bb);
                    return (
                        <line key={`bond-${a}-${b}`}
                            x1={pa.cx} y1={pa.cy} x2={pb.cx} y2={pb.cy}
                            stroke={ba.color}
                            strokeWidth={2}
                            strokeOpacity={1}
                            strokeLinecap="round"
                        />
                    );
                })}
            </svg>
            </div>

            {/* Sidebar */}
            <aside className={styles.sidebar}>
                {/* Logo / title area */}
                <div className={styles.sidebarHeader}>
                    <span className={styles.sidebarTitle}>Swarm</span>
                    <span className={styles.sidebarSubtitle}>Simulation</span>
                </div>

                {/* Connection status */}
                <div className={styles.sidebarSection}>
                    <span className={styles.sectionLabel}>Status</span>
                    <div className={`${styles.statusBadge} ${connected ? styles.statusConnected : styles.statusDisconnected}`}>
                        <div className={styles.statusDot} />
                        {connected ? "Live" : "Reconnecting…"}
                    </div>
                </div>

                <div className={styles.sidebarDivider} />

                {/* Simulation control */}
                <div className={styles.sidebarSection}>
                    <span className={styles.sectionLabel}>Simulation</span>
                    <button
                        className={`${styles.sidebarButton} ${styles.play}`}
                        onClick={handleStart}
                        disabled={!connected || running}
                    >
                        ▶ Start
                    </button>
                    <button
                        className={`${styles.sidebarButton} ${styles.reset}`}
                        onClick={handleStop}
                        disabled={!connected || !running}
                    >
                        ■ Reset
                    </button>
                    <button
                        className={`${styles.sidebarButton} ${paused ? styles.play : styles.pause}`}
                        onClick={togglePause}
                        disabled={!running || editBall}
                    >
                        <FontAwesomeIcon icon={paused ? faPlay : faPause} />
                        {paused ? " Resume" : " Pause"}
                    </button>
                    {paused && (
                        <button
                            className={`${styles.sidebarButton} ${editBall ? styles.finish : styles.edit}`}
                            onClick={handleEditBall}
                            disabled={!connected || !running}
                        >
                            ✎ {editBall ? "Finish" : "Edit Ball"}
                        </button>
                    )}
                </div>

                <div className={styles.sidebarDivider} />

                {/* Speed */}
                <div className={styles.sidebarSection}>
                    <div className={styles.sectionLabelRow}>
                        <span className={styles.sectionLabel}>Speed</span>
                        <span className={styles.sectionValue}>{speed.toFixed(1)}×</span>
                    </div>
                    <input
                        type="range"
                        min="0.1"
                        max="10"
                        step="0.1"
                        value={speed}
                        onChange={handleSpeedChange}
                        className={styles.slider}
                    />
                </div>

                <div className={styles.sidebarDivider} />

                {/* Enable controls toggle */}
                <div className={styles.sidebarSection}>
                    <label className={styles.toggleRow}>
                        <span className={styles.sectionLabel} style={{ marginBottom: 0 }}>Enable Controls</span>
                        <div
                            className={`${styles.toggleTrack} ${useControls ? styles.toggleOn : ""}`}
                            onClick={toggleUseControls}
                            role="switch"
                            aria-checked={useControls}
                        >
                            <div className={styles.toggleThumb} />
                        </div>
                    </label>
                </div>

                <div className={styles.sidebarDivider} />

                {/* Hardware color mode toggle */}
                <div className={styles.sidebarSection}>
                    <label className={styles.toggleRow}>
                        <span className={styles.sectionLabel} style={{ marginBottom: 0 }}>
                            Algorithm Colors
                        </span>
                        <div
                            className={`${styles.toggleTrack} ${useAlgorithmColors ? styles.toggleOn : ""}`}
                            onClick={toggleUseAlgorithmColors}
                            role="switch"
                            aria-checked={useAlgorithmColors}
                        >
                            <div className={styles.toggleThumb} />
                        </div>
                    </label>
                </div>
            </aside>

        </div>
    );
}