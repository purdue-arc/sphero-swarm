import { faCirclePlay, faSmile } from "@fortawesome/free-regular-svg-icons";
import styles from "./sidebar.module.css"
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faGear } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

interface SidebarLink {
    code: string,
    display: string,
    icon: IconDefinition
}

export function Sidebar({ currentView, setCurrentView}: { currentView: string, setCurrentView: (view: string) => void }) {

    const elements: SidebarLink[] = [
        { code: "run", display: "Runner", icon: faCirclePlay },
        { code: "config", display: "Configuration", icon: faGear },
        { code: "idk", display: "Helper", icon: faSmile },
    ]

    return (
        <aside className={styles.mainBar}>
            <div className={styles.header}>
                <h2 className={styles.title}>Sphero Swarm</h2>
            </div>
            
            <nav className={styles.navigation}>
                {elements.map((elm) => (
                    <button 
                        key={elm.code}
                        className={`${styles.button} ${currentView === elm.code ? styles.active : ''}`}
                        onClick={() => setCurrentView(elm.code)}
                        aria-current={currentView === elm.code ? 'page' : undefined}
                    >
                        <FontAwesomeIcon icon={elm.icon} className={styles.icon} />
                        <span className={styles.label}>{elm.display}</span>
                    </button>
                ))}
            </nav>
        </aside>
    );
}