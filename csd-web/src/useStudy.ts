import { useCallback, useEffect, useRef, useState } from 'react'
import { api as defaultApi } from './api/client'
import type { Api } from './api/client'
import type { Branch, Operation, ScheduleGrid, Version, VersionSummary } from './api/types'

export interface StudyState {
  versions: VersionSummary[]
  branches: Branch[]
  version: Version | null
  grid: ScheduleGrid | null
  operationTypes: string[]
  error: string | null
  busy: boolean
  select: (versionId: string) => void
  apply: (operation: Operation) => void
  dismissError: () => void
}

const message = (error: unknown) => (error instanceof Error ? error.message : String(error))

/** Loads a study's versions and branches and applies operations to the selected version. */
export function useStudy(studyId: string, api: Api = defaultApi): StudyState {
  const [versions, setVersions] = useState<VersionSummary[]>([])
  const [branches, setBranches] = useState<Branch[]>([])
  const [version, setVersion] = useState<Version | null>(null)
  const [grid, setGrid] = useState<ScheduleGrid | null>(null)
  const [operationTypes, setOperationTypes] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)
  const requested = useRef<string | null>(null)

  const show = useCallback(
    async (versionId: string) => {
      requested.current = versionId
      const [nextVersion, nextGrid] = await Promise.all([
        api.version(versionId),
        api.schedule(versionId),
      ])
      if (requested.current !== versionId) return // a newer selection won
      setVersion(nextVersion)
      setGrid(nextGrid)
    },
    [api],
  )

  const refreshLists = useCallback(async () => {
    const [nextVersions, nextBranches] = await Promise.all([
      api.versions(studyId),
      api.branches(studyId),
    ])
    setVersions(nextVersions)
    setBranches(nextBranches)
    return nextBranches
  }, [api, studyId])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [nextBranches, types] = await Promise.all([refreshLists(), api.operationTypes()])
        if (cancelled) return
        setOperationTypes(types)
        const main = nextBranches.find((branch) => branch.name === 'main') ?? nextBranches[0]
        if (main) await show(main.head_version_id)
      } catch (caught) {
        if (!cancelled) setError(`Could not load study ${studyId}: ${message(caught)}`)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [api, refreshLists, show, studyId])

  const select = useCallback(
    (versionId: string) => {
      show(versionId).catch((caught: unknown) => setError(message(caught)))
    },
    [show],
  )

  const apply = useCallback(
    (operation: Operation) => {
      if (busyRef.current || !version) return
      busyRef.current = true
      setBusy(true)
      setError(null)
      ;(async () => {
        try {
          const created = await api.applyOperation(version.id, operation)
          await Promise.all([refreshLists(), show(created.id)])
        } catch (caught) {
          setError(message(caught))
        } finally {
          busyRef.current = false
          setBusy(false)
        }
      })()
    },
    [api, refreshLists, show, version],
  )

  const dismissError = useCallback(() => setError(null), [])

  return { versions, branches, version, grid, operationTypes, error, busy, select, apply, dismissError }
}
