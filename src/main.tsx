import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from './context/ThemeContext.tsx'
import { TorrentProvider } from './context/TorrentContext.tsx'
import { UIProvider } from './context/UIContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <TorrentProvider>
        <UIProvider>
          <App />
        </UIProvider>
      </TorrentProvider>
    </ThemeProvider>
  </StrictMode>,
)
