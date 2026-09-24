import { describe, expect, it, vi } from 'vitest'
import { useSubstitutions } from './useSubstitutions'
import type { SuggestionsResponse } from '@/types'

const response = (branch = 'branch'): SuggestionsResponse => ({ branch_id: branch, evaluated_at: '2026-06-01', items: [] })
const request = { branch_id: 'branch', items: [{ product_id: 'original', quantity: '2' }] }

describe('memory-only substitutions', () => {
  it('does not select suggestions and keeps selection scoped by branch and line', async () => {
    const state = useSubstitutions({ substitutions: vi.fn().mockResolvedValue(response()) })
    await state.search(request)
    expect(state.selections.value).toEqual([])
    state.select('branch', 'original', 'replacement')
    state.select('other', 'original', 'second')
    state.select('branch', 'original', 'changed')
    expect(state.selections.value).toHaveLength(2)
    state.select('branch', 'original', null)
    expect(state.selections.value[0].branch_id).toBe('other')
    state.restore('other')
    expect(state.selections.value).toEqual([])
  })

  it('retains selections on price refresh but clears them on basket changes', async () => {
    const state = useSubstitutions({ substitutions: vi.fn().mockResolvedValue(response()) })
    state.select('branch', 'original', 'replacement')
    await state.search(request)
    state.invalidate()
    expect(state.suggestions.value).toEqual({})
    expect(state.selections.value).toHaveLength(1)
    state.invalidate(true)
    expect(state.selections.value).toEqual([])
  })

  it('ignores responses and errors from a previous basket', async () => {
    let finish!: (response: SuggestionsResponse) => void
    const state = useSubstitutions({ substitutions: () => new Promise((resolve) => { finish = resolve }) })
    const pending = state.search(request)
    expect(state.pending.value.branch).toBe(true)
    state.invalidate(true)
    finish(response())
    await pending
    expect(state.suggestions.value).toEqual({})
    expect(state.pending.value).toEqual({})
  })

  it('keeps only the newest response for each branch and reports recoverable errors', async () => {
    let finish!: (response: SuggestionsResponse) => void
    const fetch = vi.fn().mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
      .mockResolvedValueOnce({ ...response(), evaluated_at: 'new' })
      .mockRejectedValueOnce(new Error('Sin conexión'))
    const state = useSubstitutions({ substitutions: fetch })
    const first = state.search(request)
    await state.search(request)
    finish(response())
    await first
    expect(state.suggestions.value.branch.evaluated_at).toBe('new')
    await state.search(request)
    expect(state.errors.value.branch).toBe('Sin conexión')
    expect(state.pending.value.branch).toBe(false)
  })
})
