import { useEffect, useState } from "react";
import styles from "./config.module.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSave, faRotateLeft } from "@fortawesome/free-solid-svg-icons";
import type { SpheroConstants } from "../../types/swarm_types";

interface ConfigProps {
    constants: SpheroConstants;
    onUpdate: (newConstants: SpheroConstants) => void;
}

export function Config({ constants, onUpdate }: ConfigProps) {
    const [formData, setFormData] = useState<SpheroConstants>(constants);
    const [hasChanges, setHasChanges] = useState(false);

    useEffect(() => {
        setFormData(constants);
    }, [constants]);

    const handleInputChange = (field: keyof SpheroConstants, value: any) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));
        setHasChanges(true);
    };

    const handleArrayChange = (field: keyof SpheroConstants, index: number, value: string, subIndex?: number) => {
        const currentArray = formData[field] as any[];
        const newArray = [...currentArray];
        
        if (subIndex !== undefined) {
            // For nested arrays like INITIAL_POSITIONS
            newArray[index] = [...newArray[index]];
            newArray[index][subIndex] = parseFloat(value) || 0;
        } else {
            newArray[index] = value;
        }
        
        setFormData(prev => ({
            ...prev,
            [field]: newArray
        }));
        setHasChanges(true);
    };

    const addArrayItem = (field: keyof SpheroConstants) => {
        const currentArray = formData[field] as any[];
        let newItem: any;
        
        if (field === 'SPHERO_TAGS') {
            newItem = 'SB-XXXX';
        } else if (field === 'INITIAL_POSITIONS') {
            newItem = [0, 0];
        }
        
        setFormData(prev => ({
            ...prev,
            [field]: [...currentArray, newItem]
        }));
        setHasChanges(true);
    };

    const removeArrayItem = (field: keyof SpheroConstants, index: number) => {
        const currentArray = formData[field] as any[];
        const newArray = currentArray.filter((_, i) => i !== index);
        
        setFormData(prev => ({
            ...prev,
            [field]: newArray
        }));
        setHasChanges(true);
    };

    const handleSave = () => {
        onUpdate(formData);
        setHasChanges(false);
    };

    const handleReset = () => {
        setFormData(constants);
        setHasChanges(false);
    };

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div>
                    <h1 className={styles.title}>Configuration</h1>
                    <p className={styles.subtitle}>Adjust swarm parameters and robot settings</p>
                </div>
                <div className={styles.headerActions}>
                    <button
                        className={`${styles.actionButton} ${styles.resetButton}`}
                        onClick={handleReset}
                        disabled={!hasChanges}
                    >
                        <FontAwesomeIcon icon={faRotateLeft} className={styles.buttonIcon} />
                        Reset
                    </button>
                    <button
                        className={`${styles.actionButton} ${styles.saveButton}`}
                        onClick={handleSave}
                        disabled={!hasChanges}
                    >
                        <FontAwesomeIcon icon={faSave} className={styles.buttonIcon} />
                        Save Changes
                    </button>
                </div>
            </div>

            <div className={styles.content}>
                {/* Grid Configuration */}
                <section className={styles.section}>
                    <h2 className={styles.sectionTitle}>Grid Configuration</h2>
                    <div className={styles.formGrid}>
                        <div className={styles.formGroup}>
                            <label className={styles.label}>Grid Width (nodes)</label>
                            <input
                                type="number"
                                className={styles.input}
                                value={formData.GRID_WIDTH}
                                onChange={(e) => handleInputChange('GRID_WIDTH', parseInt(e.target.value) || 0)}
                                min="2"
                            />
                            <span className={styles.hint}>Number of nodes widthwise</span>
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.label}>Grid Height (nodes)</label>
                            <input
                                type="number"
                                className={styles.input}
                                value={formData.GRID_HEIGHT}
                                onChange={(e) => handleInputChange('GRID_HEIGHT', parseInt(e.target.value) || 0)}
                                min="2"
                            />
                            <span className={styles.hint}>Number of nodes heightwise</span>
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.label}>Node Distance (px)</label>
                            <input
                                type="number"
                                className={styles.input}
                                value={formData.SIM_DIST}
                                onChange={(e) => handleInputChange('SIM_DIST', parseInt(e.target.value) || 0)}
                                min="10"
                            />
                            <span className={styles.hint}>Pixel distance between nodes</span>
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.label}>Margin</label>
                            <input
                                type="number"
                                className={styles.input}
                                value={formData.MARGIN}
                                onChange={(e) => handleInputChange('MARGIN', parseInt(e.target.value) || 0)}
                                min="0"
                            />
                            <span className={styles.hint}>Grid boundary margin</span>
                        </div>
                    </div>

                    <div className={styles.infoBox}>
                        <div className={styles.infoItem}>
                            <span className={styles.infoLabel}>Simulation Width:</span>
                            <span className={styles.infoValue}>{(formData.GRID_WIDTH - 1) * formData.SIM_DIST} px</span>
                        </div>
                        <div className={styles.infoItem}>
                            <span className={styles.infoLabel}>Simulation Height:</span>
                            <span className={styles.infoValue}>{(formData.GRID_HEIGHT - 1) * formData.SIM_DIST} px</span>
                        </div>
                    </div>
                </section>

                {/* Robot Configuration */}
                <section className={styles.section}>
                    <h2 className={styles.sectionTitle}>Robot Configuration</h2>
                    <div className={styles.formGrid}>
                        <div className={styles.formGroup}>
                            <label className={styles.label}>Number of Spheros</label>
                            <input
                                type="number"
                                className={styles.input}
                                value={formData.N_SPHEROS}
                                onChange={(e) => handleInputChange('N_SPHEROS', parseInt(e.target.value) || 0)}
                                min="1"
                                max="10"
                            />
                            <span className={styles.hint}>Total robots in swarm</span>
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.label}>Robot Radius (px)</label>
                            <input
                                type="number"
                                className={styles.input}
                                value={formData.SPHERO_SIM_RADIUS}
                                onChange={(e) => handleInputChange('SPHERO_SIM_RADIUS', parseInt(e.target.value) || 0)}
                                min="5"
                            />
                            <span className={styles.hint}>Visual radius in simulation</span>
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.label}>Directions</label>
                            <input
                                type="number"
                                className={styles.input}
                                value={formData.DIRECTIONS}
                                onChange={(e) => handleInputChange('DIRECTIONS', parseInt(e.target.value) || 0)}
                                min="4"
                                max="8"
                            />
                            <span className={styles.hint}>Movement directions (4 or 8)</span>
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.label}>Frames</label>
                            <input
                                type="number"
                                className={styles.input}
                                value={formData.FRAMES}
                                onChange={(e) => handleInputChange('FRAMES', parseInt(e.target.value) || 0)}
                                min="30"
                            />
                            <span className={styles.hint}>Simulation frame rate</span>
                        </div>
                    </div>
                </section>

                {/* Movement Parameters */}
                <section className={styles.section}>
                    <h2 className={styles.sectionTitle}>Movement Parameters</h2>
                    <div className={styles.formGrid}>
                        <div className={styles.formGroup}>
                            <label className={styles.label}>Speed</label>
                            <input
                                type="number"
                                className={styles.input}
                                value={formData.SPHERO_SPEED}
                                onChange={(e) => handleInputChange('SPHERO_SPEED', parseInt(e.target.value) || 0)}
                                min="1"
                                max="255"
                            />
                            <span className={styles.hint}>Standard movement speed</span>
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.label}>Diagonal Speed</label>
                            <input
                                type="number"
                                className={styles.input}
                                value={formData.SPHERO_DIAGONAL_SPEED}
                                onChange={(e) => handleInputChange('SPHERO_DIAGONAL_SPEED', parseInt(e.target.value) || 0)}
                                min="1"
                                max="255"
                            />
                            <span className={styles.hint}>Diagonal movement speed</span>
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.label}>Roll Duration (s)</label>
                            <input
                                type="number"
                                step="0.1"
                                className={styles.input}
                                value={formData.ROLL_DURATION}
                                onChange={(e) => handleInputChange('ROLL_DURATION', parseFloat(e.target.value) || 0)}
                                min="0.1"
                            />
                            <span className={styles.hint}>Time for one roll action</span>
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.label}>Turn Duration (s)</label>
                            <input
                                type="number"
                                step="0.1"
                                className={styles.input}
                                value={formData.TURN_DURATION}
                                onChange={(e) => handleInputChange('TURN_DURATION', parseFloat(e.target.value) || 0)}
                                min="0.1"
                            />
                            <span className={styles.hint}>Time for one turn action</span>
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.label}>Epsilon</label>
                            <input
                                type="number"
                                step="0.001"
                                className={styles.input}
                                value={formData.EPSILON}
                                onChange={(e) => handleInputChange('EPSILON', parseFloat(e.target.value) || 0)}
                                min="0"
                            />
                            <span className={styles.hint}>Precision tolerance</span>
                        </div>
                    </div>
                </section>

                {/* Sphero Tags */}
                <section className={styles.section}>
                    <div className={styles.sectionHeader}>
                        <h2 className={styles.sectionTitle}>Sphero Tags</h2>
                        <button
                            className={styles.addButton}
                            onClick={() => addArrayItem('SPHERO_TAGS')}
                        >
                            + Add Tag
                        </button>
                    </div>
                    <div className={styles.tagsList}>
                        {formData.SPHERO_TAGS.map((tag, index) => (
                            <div key={index} className={styles.tagItem}>
                                <div className={styles.tagIndex}>{index + 1}</div>
                                <input
                                    type="text"
                                    className={styles.tagInput}
                                    value={tag}
                                    onChange={(e) => handleArrayChange('SPHERO_TAGS', index, e.target.value)}
                                    placeholder="SB-XXXX"
                                />
                                <button
                                    className={styles.removeButton}
                                    onClick={() => removeArrayItem('SPHERO_TAGS', index)}
                                    disabled={formData.SPHERO_TAGS.length <= 1}
                                >
                                    ×
                                </button>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Initial Positions */}
                <section className={styles.section}>
                    <div className={styles.sectionHeader}>
                        <h2 className={styles.sectionTitle}>Initial Positions</h2>
                        <button
                            className={styles.addButton}
                            onClick={() => addArrayItem('INITIAL_POSITIONS')}
                        >
                            + Add Position
                        </button>
                    </div>
                    <div className={styles.positionsList}>
                        {formData.INITIAL_POSITIONS.map((position, index) => (
                            <div key={index} className={styles.positionItem}>
                                <div className={styles.positionIndex}>Robot {index + 1}</div>
                                <div className={styles.positionInputs}>
                                    <div className={styles.coordinateGroup}>
                                        <label className={styles.coordinateLabel}>X</label>
                                        <input
                                            type="number"
                                            className={styles.coordinateInput}
                                            value={position[0]}
                                            onChange={(e) => handleArrayChange('INITIAL_POSITIONS', index, e.target.value, 0)}
                                            min="0"
                                            max={formData.GRID_WIDTH - 1}
                                        />
                                    </div>
                                    <div className={styles.coordinateGroup}>
                                        <label className={styles.coordinateLabel}>Y</label>
                                        <input
                                            type="number"
                                            className={styles.coordinateInput}
                                            value={position[1]}
                                            onChange={(e) => handleArrayChange('INITIAL_POSITIONS', index, e.target.value, 1)}
                                            min="0"
                                            max={formData.GRID_HEIGHT - 1}
                                        />
                                    </div>
                                </div>
                                <button
                                    className={styles.removeButton}
                                    onClick={() => removeArrayItem('INITIAL_POSITIONS', index)}
                                    disabled={formData.INITIAL_POSITIONS.length <= 1}
                                >
                                    ×
                                </button>
                            </div>
                        ))}
                    </div>
                </section>
            </div>
        </div>
    );
}