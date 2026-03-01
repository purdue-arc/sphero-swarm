import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import styles from "./sidebar.module.css";
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import {
    faChartLine,
    faEye,
    faBrain,
    faGear,
    faFlask,
    faCog,
    faInfoCircle,
    faRobot,
    faCircle,
    faPowerOff,
} from "@fortawesome/free-solid-svg-icons";

interface SidebarLink {
    code: string;
    display: string;
    icon: IconDefinition;
    badge?: string | number;
}

interface SidebarSection {
    label?: string;
    links: SidebarLink[];
}

export function Sidebar({
    currentView,
    setCurrentView,
    systemStatus = "operational",
    connectedRobots = 0,
}: {
    currentView: string;
    setCurrentView: (view: string) => void;
    systemStatus?: string;
    connectedRobots?: number;
}) {
    const sections: SidebarSection[] = [
        {
            label: "Overview",
            links: [
                {
                    code: "dashboard",
                    display: "Dashboard",
                    icon: faChartLine,
                },
            ],
        },
        {
            label: "Subsystems",
            links: [
                {
                    code: "perception",
                    display: "Perception",
                    icon: faEye,
                },
                {
                    code: "algorithms",
                    display: "Algorithms",
                    icon: faBrain,
                },
                {
                    code: "controls",
                    display: "Controls",
                    icon: faGear,
                },
            ],
        },
        {
            label: "Tools",
            links: [
                {
                    code: "simulation",
                    display: "Simulation",
                    icon: faFlask,
                },
                {
                    code: "configuration",
                    display: "Configuration",
                    icon: faCog,
                },
            ],
        },
        {
            label: "Information",
            links: [
                {
                    code: "about",
                    display: "About Us",
                    icon: faInfoCircle,
                },
            ],
        },
    ];

    return (
        <aside className={styles.mainBar}>
            <div className={styles.header}>
                <div className={styles.logoContainer}>
                    <div className={styles.logo}>
                        <FontAwesomeIcon icon={faRobot} />
                    </div>
                    <div className={styles.titleContainer}>
                        <h2 className={styles.title}>Sphero Swarm</h2>
                        <p className={styles.subtitle}>v1.0.0</p>
                    </div>
                </div>
            </div>

            <nav className={styles.navigation}>
                {sections.map((section, sectionIndex) => (
                    <div key={sectionIndex}>
                        {section.label && (
                            <div className={styles.sectionLabel}>
                                {section.label}
                            </div>
                        )}
                        {section.links.map((link) => (
                            <button
                                key={link.code}
                                className={`${styles.button} ${currentView === link.code ? styles.active : ""
                                    }`}
                                onClick={() => setCurrentView(link.code)}
                                aria-current={
                                    currentView === link.code ? "page" : undefined
                                }
                            >
                                <FontAwesomeIcon
                                    icon={link.icon}
                                    className={styles.icon}
                                />
                                <span className={styles.label}>{link.display}</span>
                                {link.badge !== undefined && (
                                    <span className={styles.badge}>{link.badge}</span>
                                )}
                            </button>
                        ))}
                    </div>
                ))}
            </nav>

            <div className={styles.footer}>
                <div className={styles.statusCard}>
                    <div className={styles.statusIcon}>
                        <FontAwesomeIcon icon={faCircle} />
                    </div>
                    <div className={styles.statusInfo}>
                        <p className={styles.statusLabel}>System Status</p>
                        <p className={styles.statusValue}>
                            {connectedRobots} Robots Active
                        </p>
                    </div>
                </div>
                <button
                    className={styles.quitButton}
                    onClick={() => window.electronAPI?.quitApp()}
                >
                    <FontAwesomeIcon icon={faPowerOff} />
                    <span>Quit</span>
                </button>
            </div>
        </aside>
    );
}