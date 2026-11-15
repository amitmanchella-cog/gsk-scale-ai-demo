import { useState } from 'react'
import type { Operation } from '../api/types'
import { OPERATION_TEMPLATES } from '../lib/operations'

interface Props {
  types: string[]
  editable: boolean
  onOperation: (operation: Operation) => void
}

/** Apply any typed operation as JSON: the same body the API accepts. */
export function OperationForm({ types, editable, onOperation }: Props) {
  const [type, setType] = useState('MoveVisit')
  const [body, setBody] = useState(JSON.stringify(OPERATION_TEMPLATES.MoveVisit, null, 2))
  const [problem, setProblem] = useState<string | null>(null)

  const choose = (next: string) => {
    setType(next)
    setBody(JSON.stringify(OPERATION_TEMPLATES[next] ?? { type: next }, null, 2))
    setProblem(null)
  }

  return (
    <details className="panel" data-testid="operation-form">
      <summary>Apply any operation ({types.length} types)</summary>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          try {
            onOperation(JSON.parse(body) as Operation)
            setProblem(null)
          } catch {
            setProblem('The operation is not valid JSON.')
          }
        }}
      >
        <label>
          Operation type
          <select value={type} onChange={(event) => choose(event.target.value)}>
            {types.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
        <label>
          Body
          <textarea
            rows={8}
            spellCheck={false}
            value={body}
            onChange={(event) => setBody(event.target.value)}
          />
        </label>
        {problem && <p role="alert">{problem}</p>}
        <button type="submit" disabled={!editable}>
          Apply operation
        </button>
      </form>
    </details>
  )
}
