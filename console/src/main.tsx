import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/outfit/300.css'
import '@fontsource/outfit/400.css'
import '@fontsource/outfit/500.css'
import '@fontsource/outfit/600.css'
import '@fontsource/noto-sans-tamil/400.css'
import '@fontsource/noto-sans-tamil/500.css'
import 'maplibre-gl/dist/maplibre-gl.css'
import { setWorkerUrl } from 'maplibre-gl'
import maplibreWorker from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import './styles/tokens.css'
import './styles/global.css'
import App from './App'
import { readConfig } from './config'
import { createSource } from './data/createSource'
import { SourceProvider } from './data/SourceProvider'
import { SelectionProvider } from './state/SelectionProvider'

// MapLibre 6 looks for its worker next to its own module, which a bundle
// doesn't have; let Vite build the worker and hand MapLibre its URL.
setWorkerUrl(maplibreWorker)

const config = readConfig(import.meta.env, window.location.search)
const source = createSource(config)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SourceProvider source={source} config={config}>
      <SelectionProvider>
        <App />
      </SelectionProvider>
    </SourceProvider>
  </StrictMode>,
)
