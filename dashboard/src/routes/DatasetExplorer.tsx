import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { listCustomers } from '../api/customers'
import { getTicket, listTickets } from '../api/tickets'
import { queryKeys } from '../api/queryKeys'
import { AddCustomerForm } from '../components/dataset/AddCustomerForm'
import { InteractionDetailPanel } from '../components/dataset/InteractionDetailPanel'
import { InteractionTable } from '../components/dataset/InteractionTable'
import { TicketTable } from '../components/dataset/TicketTable'
import { ErrorBanner } from '../components/shared/ErrorBanner'
import { LoadingSkeleton } from '../components/shared/LoadingSkeleton'

function TicketListView() {
  const [customerId, setCustomerId] = useState('')
  const [status, setStatus] = useState('')

  const customersQuery = useQuery({
    queryKey: queryKeys.customers,
    queryFn: ({ signal }) => listCustomers(signal),
  })
  const ticketsQuery = useQuery({
    queryKey: queryKeys.tickets({ customerId, status }),
    queryFn: ({ signal }) =>
      listTickets({ customer_id: customerId || undefined, status: status || undefined }, signal),
  })

  const STATUSES = ['OPEN', 'IN_PROGRESS', 'PENDING', 'WAITING_FOR_CLIENT', 'RESOLVED', 'CLOSED']

  return (
    <div>
      <h1 className="mb-4 text-lg font-semibold text-neutral-100">Dataset Explorer</h1>

      <div className="mb-3">
        <AddCustomerForm />
      </div>

      <div className="mb-3 flex gap-2">
        <select
          value={customerId}
          onChange={(e) => setCustomerId(e.target.value)}
          className="rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-200"
        >
          <option value="">All customers</option>
          {customersQuery.data?.items.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.ticket_count})
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-200"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {ticketsQuery.isLoading && <LoadingSkeleton shape="table" count={6} />}
      {ticketsQuery.isError && (
        <ErrorBanner error={ticketsQuery.error} onRetry={() => ticketsQuery.refetch()} />
      )}
      {ticketsQuery.data && (
        <>
          <p className="mb-2 text-xs text-neutral-500">{ticketsQuery.data.total} tickets</p>
          <TicketTable tickets={ticketsQuery.data.items} />
        </>
      )}
    </div>
  )
}

function TicketDetailView({ ticketId }: { ticketId: string }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedInteractionId = searchParams.get('interactionId') ?? undefined

  const ticketQuery = useQuery({
    queryKey: queryKeys.ticket(ticketId),
    queryFn: ({ signal }) => getTicket(ticketId, signal),
  })

  if (ticketQuery.isLoading) return <LoadingSkeleton count={3} />
  if (ticketQuery.isError) {
    return <ErrorBanner error={ticketQuery.error} onRetry={() => ticketQuery.refetch()} />
  }
  if (!ticketQuery.data) return null

  const { ticket, interactions } = ticketQuery.data

  return (
    <div>
      <Link to="/dataset" className="text-xs text-neutral-500 hover:underline">
        ← All tickets
      </Link>
      <h1 className="mt-2 mb-1 text-lg font-semibold text-neutral-100">{ticket.subject}</h1>
      <div className="mb-4 flex gap-3 text-xs text-neutral-500">
        <span>{ticket.customer_name}</span>
        <span>·</span>
        <span>{ticket.category}</span>
        <span>·</span>
        <span>{ticket.status}</span>
        <span>·</span>
        <span>{ticket.interaction_count} interactions</span>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div>
          <div className="mb-1 text-xs font-medium text-neutral-400">Interactions</div>
          <InteractionTable
            interactions={interactions}
            selectedId={selectedInteractionId}
            onSelect={(id) => setSearchParams({ interactionId: id })}
          />
        </div>
        <div>
          <div className="mb-1 text-xs font-medium text-neutral-400">Interaction Detail</div>
          {selectedInteractionId ? (
            <InteractionDetailPanel interactionId={selectedInteractionId} />
          ) : (
            <p className="text-xs text-neutral-600">Select an interaction to inspect it.</p>
          )}
        </div>
      </div>
    </div>
  )
}

export function DatasetExplorer() {
  const { ticketId } = useParams()
  return ticketId ? <TicketDetailView ticketId={ticketId} /> : <TicketListView />
}
