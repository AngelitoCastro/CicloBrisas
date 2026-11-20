import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import WhatsAppDemoPage from './pages/WhatsAppDemo'
import './index.css'
const demoPreview = new URLSearchParams(window.location.search).get('vista') === 'whatsapp'

createRoot(document.getElementById('root')!).render(
    <React.StrictMode>{demoPreview ? <WhatsAppDemoPage /> : <App />}</React.StrictMode>,
)
