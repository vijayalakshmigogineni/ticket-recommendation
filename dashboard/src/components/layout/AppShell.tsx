import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full min-h-screen bg-neutral-950">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  )
}
