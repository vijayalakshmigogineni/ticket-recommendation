import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { createCustomer } from '../../api/customers'
import { ApiError } from '../../api/client'
import { queryKeys } from '../../api/queryKeys'

export function AddCustomerForm() {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [inboxEmail, setInboxEmail] = useState('')
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: createCustomer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.customers })
      setName('')
      setInboxEmail('')
      setOpen(false)
    },
  })

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded border border-neutral-800 px-2 py-1 text-xs text-neutral-300 hover:bg-neutral-900"
      >
        + Add Customer
      </button>
    )
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        mutation.mutate({ name, inbox_email: inboxEmail })
      }}
      className="mb-3 flex flex-wrap items-start gap-2 rounded border border-neutral-800 bg-neutral-900 p-2"
    >
      <input
        required
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Company name"
        className="rounded border border-neutral-800 bg-neutral-950 px-2 py-1 text-xs text-neutral-200"
      />
      <input
        required
        type="email"
        value={inboxEmail}
        onChange={(e) => setInboxEmail(e.target.value)}
        placeholder="inbox_email (e.g. billing@example.com)"
        className="w-64 rounded border border-neutral-800 bg-neutral-950 px-2 py-1 text-xs text-neutral-200"
      />
      <button
        type="submit"
        disabled={mutation.isPending}
        className="rounded bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-900 disabled:opacity-40"
      >
        {mutation.isPending ? 'Adding…' : 'Add'}
      </button>
      <button
        type="button"
        onClick={() => setOpen(false)}
        className="rounded px-2 py-1 text-xs text-neutral-500 hover:bg-neutral-800"
      >
        Cancel
      </button>
      {mutation.isError && (
        <p className="w-full text-xs text-red-400">
          {mutation.error instanceof ApiError ? mutation.error.message : 'Failed to add customer'}
        </p>
      )}
      <p className="w-full text-[11px] text-neutral-600">
        New customer starts with 0 tickets -- the pipeline will correctly find "no match" until
        you seed at least one ticket for them (edit data/sample_dataset/seed_data.py, or ask for
        one to be added).
      </p>
    </form>
  )
}
