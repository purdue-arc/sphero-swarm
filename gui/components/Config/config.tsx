import { useEffect, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    faSave,
    faRotateLeft,
    faPlus,
    faTrash,
    faRobot,
    faTableCells,
    faGaugeHigh,
    faLocationDot,
} from "@fortawesome/free-solid-svg-icons";
import type { SpheroConstants } from "../../types/swarm_types";

import s from "./config.module.css"

// All known/discoverable Sphero tags — expand as needed
const KNOWN_TAGS = [
    'SB-76B3',
    'SB-E274',
    'SB-1840',
    'SB-B11D',
    'SB-CEB2',
    'SB-BD0A',
];

interface ConfigProps {
    constants: SpheroConstants;
    onUpdate: (newConstants: SpheroConstants) => void;
}

export function Config({ constants, onUpdate }: ConfigProps) {
    const [form, setForm] = useState<SpheroConstants>(constants);
    const [hasChanges, setHasChanges] = useState(false);

    useEffect(() => {
        setForm(constants);
        setHasChanges(false);
    }, [constants]);

    const update = (field: keyof SpheroConstants, value: any) => {
        setForm(prev => ({ ...prev, [field]: value }));
        setHasChanges(true);
    };

    const updateSpheroRow = (index: number, field: "tag" | "x" | "y", value: any) => {
        const tags = [...form.SPHERO_TAGS];
        const positions = form.INITIAL_POSITIONS.map(p => [...p] as [number, number]);

        if (field === "tag") {
            tags[index] = value;
        } else if (field === "x") {
            positions[index][0] = Number(value);
        } else {
            positions[index][1] = Number(value);
        }

        setForm(prev => ({ ...prev, SPHERO_TAGS: tags, INITIAL_POSITIONS: positions }));
        setHasChanges(true);
    };

    const addSphero = () => {
        const unusedTag = KNOWN_TAGS.find(t => !form.SPHERO_TAGS.includes(t)) ?? "SB-XXXX";
        setForm(prev => ({
            ...prev,
            N_SPHEROS: prev.N_SPHEROS + 1,
            SPHERO_TAGS: [...prev.SPHERO_TAGS, unusedTag],
            INITIAL_POSITIONS: [...prev.INITIAL_POSITIONS, [0, 0]],
        }));
        setHasChanges(true);
    };

    const removeSphero = (index: number) => {
        if (form.SPHERO_TAGS.length <= 1) return;
        const tags = form.SPHERO_TAGS.filter((_, i) => i !== index);
        const positions = form.INITIAL_POSITIONS.filter((_, i) => i !== index);
        setForm(prev => ({
            ...prev,
            N_SPHEROS: prev.N_SPHEROS - 1,
            SPHERO_TAGS: tags,
            INITIAL_POSITIONS: positions,
        }));
        setHasChanges(true);
    };

    const onNSpherosChange = (val: number) => {
        const n = Math.max(1, val);
        const tags = [...form.SPHERO_TAGS];
        const positions = form.INITIAL_POSITIONS.map(p => [...p] as [number, number]);

        while (tags.length < n) {
            const unusedTag = KNOWN_TAGS.find(t => !tags.includes(t)) ?? "SB-XXXX";
            tags.push(unusedTag);
            positions.push([0, 0]);
        }

        setForm(prev => ({
            ...prev,
            N_SPHEROS: n,
            SPHERO_TAGS: tags.slice(0, n),
            INITIAL_POSITIONS: positions.slice(0, n),
        }));
        setHasChanges(true);
    };

    const save = async () => { 
        onUpdate(form);
        await window.electronAPI.saveConstants(form);
        setHasChanges(false);
    };
    const reset = () => { setForm(constants); setHasChanges(false); };

    const rows = Array.from({ length: form.N_SPHEROS }, (_, i) => ({
        tag: form.SPHERO_TAGS[i] ?? "SB-XXXX",
        x: form.INITIAL_POSITIONS[i]?.[0] ?? 0,
        y: form.INITIAL_POSITIONS[i]?.[1] ?? 0,
    }));

    const availableTagsFor = (currentTag: string) =>
        KNOWN_TAGS.filter(t => t === currentTag || !form.SPHERO_TAGS.includes(t));

    return (
        <div className={s.page}>
            {/* Header */}
            <div className={s.header}>
                <div>
                    <h1 className={s.title}>
                        {hasChanges && <span className={s.unsavedDot} />}
                        Configurations
                    </h1>
                </div>
                <div className={s.headerActions}>
                    <button className={s.actionBtn} onClick={reset} disabled={!hasChanges}>
                        <FontAwesomeIcon icon={faRotateLeft} />
                        Discard
                    </button>
                    <button className={`${s.actionBtn} ${s.actionBtnSave}`} onClick={save} disabled={!hasChanges}>
                        <FontAwesomeIcon icon={faSave} />
                        Save
                    </button>
                </div>
            </div>

            {/* Two-column grid for scalar settings */}
            <div className={s.grid}>

                <div className={s.section}>
                    <div className={s.sectionHead}>
                        <div className={s.sectionIcon}><FontAwesomeIcon icon={faTableCells} /></div>
                        <h2 className={s.sectionTitle}>Arena Grid</h2>
                    </div>
                    <div className={s.formRow}>
                        <div className={s.formGroup}>
                            <label className={s.label}>Width (nodes)</label>
                            <input
                                type="number" min={2} className={s.input}
                                value={form.GRID_WIDTH}
                                onChange={e => update("GRID_WIDTH", parseInt(e.target.value) || 2)}
                            />
                            <span className={s.hint}>Columns in the navigation grid</span>
                        </div>
                        <div className={s.formGroup}>
                            <label className={s.label}>Height (nodes)</label>
                            <input
                                type="number" min={2} className={s.input}
                                value={form.GRID_HEIGHT}
                                onChange={e => update("GRID_HEIGHT", parseInt(e.target.value) || 2)}
                            />
                            <span className={s.hint}>Rows in the navigation grid</span>
                        </div>
                    </div>
                </div>

                <div className={s.section}>
                    <div className={s.sectionHead}>
                        <div className={s.sectionIcon}><FontAwesomeIcon icon={faGaugeHigh} /></div>
                        <h2 className={s.sectionTitle}>Motion &amp; Timing</h2>
                    </div>
                    <div className={s.formRow}>
                        <div className={s.formGroup}>
                            <label className={s.label}>Speed</label>
                            <input
                                type="number" min={1} max={255} className={s.input}
                                value={form.SPHERO_SPEED}
                                onChange={e => update("SPHERO_SPEED", parseInt(e.target.value) || 0)}
                            />
                            <span className={s.hint}>Linear speed (1–255)</span>
                        </div>
                        <div className={s.formGroup}>
                            <label className={s.label}>Diagonal Speed</label>
                            <input
                                type="number" min={1} max={255} className={s.input}
                                value={form.SPHERO_DIAGONAL_SPEED}
                                onChange={e => update("SPHERO_DIAGONAL_SPEED", parseInt(e.target.value) || 0)}
                            />
                            <span className={s.hint}>≈ speed × √2, tune for accel</span>
                        </div>
                        <div className={s.formGroup}>
                            <label className={s.label}>Roll Duration (s)</label>
                            <input
                                type="number" min={0.1} step={0.05} className={s.input}
                                value={form.ROLL_DURATION}
                                onChange={e => update("ROLL_DURATION", parseFloat(e.target.value) || 0)}
                            />
                            <span className={s.hint}>Time per one-node roll</span>
                        </div>
                        <div className={s.formGroup}>
                            <label className={s.label}>Turn Duration (s)</label>
                            <input
                                type="number" min={0.1} step={0.05} className={s.input}
                                value={form.TURN_DURATION}
                                onChange={e => update("TURN_DURATION", parseFloat(e.target.value) || 0)}
                            />
                            <span className={s.hint}>Time per 90° heading change</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Full-width Sphero table */}
            <div className={s.sectionFull}>
                <div className={s.sectionHead} style={{ justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                        <div className={s.sectionIcon}><FontAwesomeIcon icon={faRobot} /></div>
                        <h2 className={s.sectionTitle}>Spheros — {form.N_SPHEROS} robot{form.N_SPHEROS !== 1 ? "s" : ""}</h2>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                        <div className={s.formGroup}>
                            <input
                                type="number" min={1} max={KNOWN_TAGS.length} className={s.input}
                                style={{ width: "72px" }}
                                value={form.N_SPHEROS}
                                onChange={e => onNSpherosChange(parseInt(e.target.value) || 1)}
                                title="Number of Spheros"
                            />
                        </div>
                    </div>
                </div>

                <table className={s.table}>
                    <thead>
                        <tr>
                            <th className={s.th} style={{ width: "48px" }}>#</th>
                            <th className={s.th}>Tag</th>
                            <th className={s.th}>
                                <span style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                                    <FontAwesomeIcon icon={faLocationDot} style={{ fontSize: "0.7rem" }} />
                                    Initial Position (x, y)
                                </span>
                            </th>
                            <th className={s.th} style={{ width: "40px" }}></th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row, i) => (
                            <tr key={i}>
                                <td className={s.td}>
                                    <span className={s.indexBadge}>{i + 1}</span>
                                </td>
                                <td className={s.td}>
                                    <select
                                        className={s.select}
                                        value={row.tag}
                                        onChange={e => updateSpheroRow(i, "tag", e.target.value)}
                                    >
                                        {availableTagsFor(row.tag).length === 0 && (
                                            <option value={row.tag}>{row.tag}</option>
                                        )}
                                        {availableTagsFor(row.tag).map(t => (
                                            <option key={t} value={t}>{t}</option>
                                        ))}
                                    </select>
                                </td>
                                <td className={s.td}>
                                    <div className={s.coordWrap}>
                                        <span className={s.coordLabel}>X</span>
                                        <input
                                            type="number" min={0} max={form.GRID_WIDTH - 1}
                                            className={s.coordInput}
                                            value={row.x}
                                            onChange={e => updateSpheroRow(i, "x", e.target.value)}
                                        />
                                        <span className={s.coordLabel} style={{ marginLeft: "0.5rem" }}>Y</span>
                                        <input
                                            type="number" min={0} max={form.GRID_HEIGHT - 1}
                                            className={s.coordInput}
                                            value={row.y}
                                            onChange={e => updateSpheroRow(i, "y", e.target.value)}
                                        />
                                    </div>
                                </td>
                                <td className={s.td}>
                                    <button
                                        className={s.deleteBtn}
                                        onClick={() => removeSphero(i)}
                                        disabled={rows.length <= 1}
                                        title="Remove sphero"
                                        onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                                        onMouseLeave={e => (e.currentTarget.style.color = "#64748b")}
                                    >
                                        <FontAwesomeIcon icon={faTrash} style={{ fontSize: "0.75rem" }} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {rows.length != KNOWN_TAGS.length && (
                    <button className={`${s.addRowBtn} ${rows.length == KNOWN_TAGS.length ? s.disabledAdd : ''}`} onClick={addSphero} disabled={rows.length == KNOWN_TAGS.length}>
                        <FontAwesomeIcon icon={faPlus} style={{ fontSize: "0.75rem" }} />
                        Add Sphero
                    </button>
                )}
            </div>
        </div>
    );
}