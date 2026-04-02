import { createContext, useContext } from 'react'
import { useAuth } from '@clerk/react'

const FinsightAuthContext = createContext({
  authEnabled: false,
  getToken: async () => null,
  userId: null,
  isSignedIn: false,
})

export function ClerkAuthBridge({ children }) {
  const { getToken, userId, isSignedIn } = useAuth()

  return (
    <FinsightAuthContext.Provider
      value={{
        authEnabled: true,
        getToken,
        userId,
        isSignedIn,
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
        userId: null,
        isSignedIn: false,
      }}
    >
      {children}
    </FinsightAuthContext.Provider>
  )
}

export function useFinsightAuth() {
  return useContext(FinsightAuthContext)
}
