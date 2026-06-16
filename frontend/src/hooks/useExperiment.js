import { useState, useCallback } from 'react'
import { fireExperiment, getResults } from '../api'

export function useExperiment() {
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function _pollUntilDone(experimentId) {
    for (let i = 0; i < 72; i++) {
      await new Promise(r => setTimeout(r, 5000))
      try {
        const r = await getResults(experimentId)
        if (r?.control?.length > 0) return r
      } catch (_) {}
    }
    throw new Error('Experiment did not complete within 6 minutes')
  }

  const fire = useCallback(async ({ prompt, knowledgeLayer, nTrials, injectionMode }) => {
    setStatus('firing')
    setError(null)

    const fetchPromise = fireExperiment({ prompt, knowledgeLayer, nTrials, injectionMode })

    try {
      const result = await Promise.race([
        fetchPromise.catch(async () => {
          setStatus('polling')
          return _pollUntilDone()
        }),
        new Promise((resolve, reject) => {
          setTimeout(async () => {
            try {
              const postResult = await fetchPromise
              resolve(postResult)
            } catch (_) {
              setStatus('polling')
              try { resolve(await _pollUntilDone()) }
              catch (e) { reject(e) }
            }
          }, 15000)
        }),
      ])
      setResult(result)
      setStatus('done')
      return result
    } catch (err) {
      setError(err.message)
      setStatus('error')
      throw err
    }
  }, [])

  return { fire, status, result, error }
}
