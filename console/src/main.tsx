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
import { readConfig } from './config'
import { createSource } from './data/createSource'
import { SourceProvider } from './data/SourceProvider'
import { SelectionProvider } from './state/SelectionProvider'

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
