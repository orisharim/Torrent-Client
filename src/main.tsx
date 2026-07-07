import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from './context/ThemeContext.tsx'
import { LanguageProvider } from './context/LanguageContext.tsx'
import { TorrentProvider } from './context/TorrentContext.tsx'
import { UIProvider } from './context/UIContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <LanguageProvider>
        <TorrentProvider>
          <UIProvider>
            <App />
          </UIProvider>
        </TorrentProvider>
      </LanguageProvider>
    </ThemeProvider>
  </StrictMode>,
)
