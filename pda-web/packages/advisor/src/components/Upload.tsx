import { useQuery } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import { api, type ApiError } from '../api';
import { indicationLabel } from '../format';
import type { SampleProtocol } from '../types';

interface Props {
  busy: boolean;
  error: ApiError | null;
  onFile: (file: File) => void;
}

export function Upload({ busy, error, onFile }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [sampleError, setSampleError] = useState<string | null>(null);
  const samples = useQuery({ queryKey: ['samples'], queryFn: api.samples });

  async function loadSample(sample: SampleProtocol) {
    setSampleError(null);
    try {
      onFile(await api.sampleFile(sample));
    } catch (cause) {
      setSampleError((cause as Error).message);
    }
  }

  return (
    <section className="pda-card" aria-labelledby="upload-heading">
      <h2 id="upload-heading">Upload a draft protocol</h2>
      <p className="pda-muted">
        Plain text or Word (.docx). The document is read once to extract the design and is not stored.
      </p>
      <div
        className={`pda-drop${dragging ? ' pda-drop--over' : ''}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          const file = event.dataTransfer.files[0];
          if (file) onFile(file);
        }}
      >
        <input
          ref={input}
          id="protocol-file"
          data-testid="protocol-file"
          className="pda-visually-hidden"
          type="file"
          accept=".txt,.md,.docx"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onFile(file);
            event.target.value = '';
          }}
        />
        <label htmlFor="protocol-file" className="pda-button pda-button--primary" aria-disabled={busy}>
          {busy ? 'Extracting…' : 'Choose a file'}
        </label>
        <span className="pda-muted pda-drop__hint">or drop it here</span>
      </div>

      {error && (
        <div role="alert" className="pda-alert">
          <strong>{error.message}</strong>
          {error.warnings.length > 0 && (
            <ul>
              {error.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <h3>Or try a synthetic sample</h3>
      {samples.isError && (
        <p role="alert" className="pda-alert">
          {(samples.error as Error).message}
        </p>
      )}
      {sampleError && (
        <p role="alert" className="pda-alert">
          {sampleError}
        </p>
      )}
      <ul className="pda-samples">
        {samples.data?.map((sample) => (
          <li key={sample.key}>
            <button
              type="button"
              className="pda-sample"
              data-testid={`sample-${sample.key}`}
              disabled={busy}
              onClick={() => void loadSample(sample)}
            >
              <span className="pda-sample__meta">
                {indicationLabel(sample.indication)}
                {sample.weak && <span className="pda-tag pda-tag--high">Deliberately weak</span>}
              </span>
              <span className="pda-sample__title">{sample.title}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
