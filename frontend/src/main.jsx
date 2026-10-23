import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import Evaluations from './Evaluations.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {window.location.pathname === '/evaluations' ? <Evaluations /> : <App />}
  </StrictMode>,
)
