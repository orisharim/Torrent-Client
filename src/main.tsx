import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from './context/ThemeContext.tsx'
import { LanguageProvider } from './context/LanguageContext.tsx'
import { TorrentProvider } from './context/TorrentContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <LanguageProvider>
        <TorrentProvider>
          <App />
        </TorrentProvider>
      </LanguageProvider>
    </ThemeProvider>
  </StrictMode>,
)
