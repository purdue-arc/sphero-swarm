import styles from './App.module.css'
import { Sidebar } from "../components/Sidebar/sidebar"
import {Runner} from "../components/Runner/runner"
import { useState } from 'react'

function App() {
  const [currentView, setCurrentView] = useState<string>("run")

  return (
    <div className={styles.mainBody}>
      <Sidebar currentView={currentView} setCurrentView={setCurrentView}/>
      <div className={styles.viewer}>
        {currentView == "run" && (
          <Runner/>
        )}

      </div>
    </div>
  )
}

export default App
