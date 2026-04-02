import React from 'react'
import ReactDOM from 'react-dom/client'
import { ClerkProvider } from '@clerk/react'
import App from './App'
import './index.css'
import { ClerkAuthBridge, FallbackAuthProvider } from './lib/finsight-auth'

const clerkPublishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {clerkPublishableKey ? (
      <ClerkProvider afterSignOutUrl="/">
        <ClerkAuthBridge>
          <App />
        </ClerkAuthBridge>
      </ClerkProvider>
    ) : (
      <FallbackAuthProvider>
        <App />
      </FallbackAuthProvider>
    )}
  </React.StrictMode>
)
