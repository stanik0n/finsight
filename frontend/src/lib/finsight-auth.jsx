import { createContext, useContext } from 'react'
import { useAuth } from '@clerk/react'

const FinsightAuthContext = createContext({
  authEnabled: false,
  getToken: async () => null,
})

export function ClerkAuthBridge({ children }) {
  const { getToken } = useAuth()

  return (
    <FinsightAuthContext.Provider
      value={{
        authEnabled: true,
        getToken,
      }}
    >
      {children}
    </FinsightAuthContext.Provider>
  )
}

export function FallbackAuthProvider({ children }) {
  return (
    <FinsightAuthContext.Provider
      value={{
        authEnabled: false,
        getToken: async () => null,
      }}
    >
      {children}
    </FinsightAuthContext.Provider>
  )
}

export function useFinsightAuth() {
  return useContext(FinsightAuthContext)
}
