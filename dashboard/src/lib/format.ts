export function formatMs(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

export function formatScore(score: number, digits = 3): string {
  return score.toFixed(digits)
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

export function truncate(text: string, max = 200): string {
  if (text.length <= max) return text
  return `${text.slice(0, max)}…`
}

export function durationTier(ms: number): 'fast' | 'medium' | 'slow' {
  if (ms < 500) return 'fast'
  if (ms < 5000) return 'medium'
  return 'slow'
}
