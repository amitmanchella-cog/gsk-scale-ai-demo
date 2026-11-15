import { useCallback, useEffect, useRef, useState } from 'react'
import { api as defaultApi } from './api/client'
import type { Api } from './api/client'
import type { Branch, Operation, ScheduleGrid, Score, Version, VersionSummary } from './api/types'

export interface StudyState {
  versions: VersionSummary[]
  branches: Branch[]
  /** The branch being viewed and edited. */
  branchName: string
  score: Score | null
  version: Version | null
  grid: ScheduleGrid | null
  operationTypes: string[]
  error: string | null
  busy: boolean
  select: (versionId: string) => void
  apply: (operation: Operation) => void
  selectBranch: (name: string) => void
  /** Start a branch from the version on screen and switch to it. */
  createBranch: (name: string) => void
  dismissError: () => void
}

const message = (error: unknown) => (error instanceof Error ? error.message : String(error))

/** Loads a study's versions and branches and applies operations to the selected version. */
export function useStudy(studyId: string, api: Api = defaultApi): StudyState {
  const [versions, setVersions] = useState<VersionSummary[]>([])
  const [branches, setBranches] = useState<Branch[]>([])
  const [version, setVersion] = useState<Version | null>(null)
  const [grid, setGrid] = useState<ScheduleGrid | null>(null)
  const [score, setScore] = useState<Score | null>(null)
  const [branchName, setBranchName] = useState('main')
  const [operationTypes, setOperationTypes] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)
  const requested = useRef<string | null>(null)

  const show = useCallback(
    async (versionId: string) => {
      requested.current = versionId
      const [nextVersion, nextGrid, nextScore] = await Promise.all([
        api.version(versionId),
        api.schedule(versionId),
        api.score(versionId),
      ])
      if (requested.current !== versionId) return // a newer selection won
      setVersion(nextVersion)
      setGrid(nextGrid)
      setScore(nextScore)
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

  const run = useCallback((work: () => Promise<void>) => {
    if (busyRef.current) return
    busyRef.current = true
    setBusy(true)
    setError(null)
    work()
      .catch((caught: unknown) => setError(message(caught)))
      .finally(() => {
        busyRef.current = false
        setBusy(false)
      })
  }, [])

  const apply = useCallback(
    (operation: Operation) => {
      if (!version) return
      run(async () => {
        const created = await api.applyOperation(version.id, operation, branchName)
        await Promise.all([refreshLists(), show(created.id)])
      })
    },
    [api, branchName, refreshLists, run, show, version],
  )

  const selectBranch = useCallback(
    (name: string) => {
      const branch = branches.find((candidate) => candidate.name === name)
      if (!branch) return
      setBranchName(name)
      select(branch.head_version_id)
    },
    [branches, select],
  )

  const createBranch = useCallback(
    (name: string) => {
      if (!version) return
      run(async () => {
        const created = await api.createBranch(version.id, name)
        await refreshLists()
        setBranchName(created.name)
      })
    },
    [api, refreshLists, run, version],
  )

  const dismissError = useCallback(() => setError(null), [])

  return {
    versions,
    branches,
    branchName,
    score,
    version,
    grid,
    operationTypes,
    error,
    busy,
    select,
    apply,
    selectBranch,
    createBranch,
    dismissError,
  }
}
