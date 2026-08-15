import { useState, useRef, useEffect } from 'react';
import AgentTrace from './AgentTrace';
import RiskBadge from './RiskBadge';
import useAgentTrace from '../hooks/useAgentTrace';
import * as ap from '../api/ap';

export default function UploadInvoice({ onUploadComplete }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [processingPhase, setProcessingPhase] = useState('idle');
  const [jobId, setJobId] = useState(null);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef(null);

  const { agents, finalInvoice, isComplete, isFailed, error: traceError, reset } =
    useAgentTrace(jobId, processingPhase === 'processing' || processingPhase === 'done');

  useEffect(() => {
    if (isComplete && finalInvoice) {
      setProcessingPhase('done');
      onUploadComplete?.();
      const t = setTimeout(() => {
        setFile(null);
        setJobId(null);
        setProcessingPhase('idle');
        reset();
      }, 2500);
      return () => clearTimeout(t);
    }
    return undefined;
  }, [isComplete, finalInvoice, onUploadComplete, reset]);

  useEffect(() => {
    if (isFailed) {
      setError(traceError || 'Processing failed');
      setProcessingPhase('idle');
      setJobId(null);
      reset();
    }
  }, [isFailed, traceError, reset]);

  const validateFile = (f) => {
    if (!f) return false;
    if (f.type !== 'application/pdf' && !f.name.toLowerCase().endsWith('.pdf')) {
      setError('Please upload a PDF file');
      return false;
    }
    setError('');
    return true;
  };

  const handleFile = (f) => {
    if (validateFile(f)) {
      setFile(f);
      setProcessingPhase('idle');
      reset();
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const handleProcess = async () => {
    if (!file || uploading) return;
    setUploading(true);
    setError('');

    const { data, error: uploadError } = await ap.uploadInvoice(file);
    setUploading(false);

    if (uploadError || !data?.jobId) {
      setError(uploadError || 'Upload failed');
      return;
    }

    setJobId(data.jobId);
    setProcessingPhase('processing');
  };

  const isRunning = processingPhase === 'processing' && !isComplete && !isFailed;

  return (
    <div className="rounded-xl border border-border bg-surface p-6">
      <h2 className="mb-4 text-lg font-semibold text-text-primary">Upload Invoice</h2>

      {processingPhase === 'idle' && (
        <>
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed px-6 py-10 transition-default ${
              dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
            }`}
          >
            <svg className="mb-3 h-10 w-10 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-sm text-text-secondary">Drop invoice PDF here or click to browse</p>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={(e) => handleFile(e.target.files[0])}
            />
          </div>

          {error && <p className="mt-2 text-sm text-danger">{error}</p>}

          {file && (
            <div className="mt-4 flex items-center justify-between rounded-lg border border-border bg-surface-elevated px-4 py-3">
              <span className="truncate font-mono text-sm text-text-primary">{file.name}</span>
              <button
                onClick={handleProcess}
                disabled={uploading}
                className="ml-4 shrink-0 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-default hover:bg-primary/90 disabled:opacity-70"
              >
                {uploading ? 'Uploading...' : 'Process Invoice →'}
              </button>
            </div>
          )}
        </>
      )}

      {(processingPhase === 'processing' || processingPhase === 'done') && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            {isRunning && (
              <svg className="spinner h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            <span className="text-sm text-text-secondary">
              {isComplete ? 'Processing complete' : 'Agents processing...'}
            </span>
          </div>

          <AgentTrace agents={agents} />

          {isComplete && finalInvoice && (
            <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-surface-elevated px-4 py-3">
              <span className="text-sm text-text-primary">Invoice processed —</span>
              <span className="text-sm text-text-secondary">Risk:</span>
              <RiskBadge risk={finalInvoice.risk?.toUpperCase()} />
              <span className="ml-auto font-mono text-xs text-text-muted">{finalInvoice.number}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
