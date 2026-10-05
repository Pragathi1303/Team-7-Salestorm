import { useState, useEffect } from 'react'

export function useCountdown(endTime) {
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    if (!endTime) return
    const calc = () => {
      const diff = Math.max(0, Math.floor((new Date(endTime) - Date.now()) / 1000))
      setSeconds(diff)
    }
    calc()
    const id = setInterval(calc, 1000)
    return () => clearInterval(id)
  }, [endTime])

  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  const pad = n => String(n).padStart(2, '0')

  let display
  if (h > 0) display = `${pad(h)}:${pad(m)}:${pad(s)}`
  else display = `${pad(m)}:${pad(s)}`

  return { seconds, display, expired: seconds === 0 && !!endTime }
}
