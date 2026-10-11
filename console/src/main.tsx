import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/outfit/300.css'
import '@fontsource/outfit/400.css'
import '@fontsource/outfit/500.css'
import '@fontsource/outfit/600.css'
import '@fontsource/noto-sans-tamil/400.css'
import '@fontsource/noto-sans-tamil/500.css'
import 'maplibre-gl/dist/maplibre-gl.css'
import './styles/tokens.css'
import './styles/global.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
