import { useState } from 'react'
import type { Branch } from '../api/types'

interface Props {
  branches: Branch[]
  current: string
  canCreate: boolean
  /** The version a new branch would start from, for example "v2". */
  versionLabel: string
  onSelect: (name: string) => void
  onCreate: (name: string) => void
}

const VALID = /^[a-z0-9][a-z0-9-]{0,62}$/

export function BranchPanel({ branches, current, canCreate, versionLabel, onSelect, onCreate }: Props) {
  const [name, setName] = useState('')
  const taken = branches.some((branch) => branch.name === name)
  const valid = VALID.test(name) && !taken

  return (
    <section className="panel branch-panel" aria-label="Branches">
      <h2>
        Branches <span className="badge">{branches.length}</span>
      </h2>
      <label>
        Viewing
        <select
          data-testid="branch-select"
          value={current}
          onChange={(event) => onSelect(event.target.value)}
        >
          {branches.map((branch) => (
            <option key={branch.name}>{branch.name}</option>
          ))}
        </select>
      </label>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          if (!valid || !canCreate) return
          onCreate(name)
          setName('')
        }}
      >
        <label>
          New branch from {versionLabel}
          <input
            data-testid="branch-name"
            placeholder="fewer-visits"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        {name !== '' && !valid && (
          <p className="hint" data-testid="branch-name-problem">
            {taken ? 'That branch already exists.' : 'Use lower-case letters, digits and dashes.'}
          </p>
        )}
        <button type="submit" data-testid="create-branch" disabled={!valid || !canCreate}>
          Create branch
        </button>
      </form>
    </section>
  )
}
