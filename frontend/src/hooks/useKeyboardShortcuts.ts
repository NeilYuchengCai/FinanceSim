import { useState, useEffect, useCallback, useRef } from 'react'

interface ShortcutConfig {
  key: string
  ctrlKey?: boolean
  metaKey?: boolean
  action: () => void
  description: string
}

export function useKeyboardShortcuts(shortcuts: ShortcutConfig[]) {
  const shortcutsRef = useRef(shortcuts)
  shortcutsRef.current = shortcuts

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const match = shortcutsRef.current.find(s => {
        if (s.key.toLowerCase() !== e.key.toLowerCase()) return false
        if (s.ctrlKey && !e.ctrlKey) return false
        if (s.metaKey && !e.metaKey) return false
        return true
      })

      if (match) {
        e.preventDefault()
        match.action()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])
}

export function useGlobalSearch() {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')

  const open = useCallback(() => setIsOpen(true), [])
  const close = useCallback(() => {
    setIsOpen(false)
    setQuery('')
  }, [])

  useKeyboardShortcuts([
    {
      key: 'k',
      metaKey: true,
      action: open,
      description: 'Open Search'
    },
    {
      key: 'Escape',
      action: close,
      description: 'Close Search'
    }
  ])

  return { isOpen, query, setQuery, open, close }
}
