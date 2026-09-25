import { createContext, useContext, useState, useEffect } from 'react'
import type { ReactNode } from 'react'

export type ThemeMode = 'dark' | 'light'

interface ThemeContextType {
  theme: ThemeMode
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('financesim-theme')
    return (saved === 'light' || saved === 'dark') ? saved : 'dark'
  })

  useEffect(() => {
    localStorage.setItem('financesim-theme', theme)
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used within ThemeProvider')
  return context
}
