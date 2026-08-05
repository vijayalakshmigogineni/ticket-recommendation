import { useState } from 'react'

export function CodeBlock({ text, label }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="rounded border border-neutral-800 bg-neutral-950">
      <div className="flex items-center justify-between border-b border-neutral-800 px-2 py-1">
        <span className="text-xs text-neutral-500">{label}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="rounded px-1.5 py-0.5 text-xs text-neutral-400 hover:bg-neutral-800"
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="max-h-96 overflow-auto whitespace-pre-wrap p-2 font-mono text-xs text-neutral-300">
        {text}
      </pre>
    </div>
  )
}
