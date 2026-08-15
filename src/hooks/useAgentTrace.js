import { useState, useEffect, useCallback } from 'react';
import { getJobStatus, getInvoice } from '../api/ap';
import { formatConfidence } from '../utils/normalize';

const AGENT_NAMES = [
  'Invoice Parser',
  'PO Matcher',
  'Duplicate Detector',
  'Fraud Signal',
  'Risk Scorer',
  'Approval Router',
];

/** Delay between each agent trace step shown in the UI */
const STEP_MS = 1000;

function initialAgents() {
  return AGENT_NAMES.map((name) => ({
    agent: name,
    result: null,
    confidence: null,
    model: null,
    status: null,
    detail: null,
    state: 'pending',
  }));
}

function agentIndex(name) {
  const n = (name || '').toLowerCase();
  return AGENT_NAMES.findIndex((a) => a.toLowerCase() === n || n.includes(a.toLowerCase().split(' ')[0]));
}

export function useAgentTrace(jobId, enabled = true) {
  const [agents, setAgents] = useState(initialAgents);
  const [finalInvoice, setFinalInvoice] = useState(null);
  const [isComplete, setIsComplete] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const [error, setError] = useState(null);

  const reset = useCallback(() => {
    setAgents(initialAgents());
    setFinalInvoice(null);
    setIsComplete(false);
    setIsFailed(false);
    setError(null);
  }, []);

  const updateAgent = useCallback((agentName, patch) => {
    setAgents((prev) => {
      const idx = agentIndex(agentName);
      if (idx < 0) return prev;
      const next = [...prev];
      next[idx] = { ...next[idx], ...patch };
      return next;
    });
  }, []);

  useEffect(() => {
    if (!jobId) {
      reset();
      return undefined;
    }
    if (!enabled) {
      return undefined;
    }

    reset();

    let active = true;
    let ws = null;
    let pollTimer = null;
    let stepTimer = null;
    let finished = false;

    const eventQueue = [];
    let pendingCompleteInvoice = null;
    let pendingFailedError = null;
    let terminalEnqueued = false;

    const stopPolling = () => {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    };

    const stopStepTimer = () => {
      if (stepTimer) {
        clearTimeout(stepTimer);
        stepTimer = null;
      }
    };

    const applyEvent = (event) => {
      if (event.type === 'agent_start') {
        updateAgent(event.agent?.name || event.agent, { state: 'running' });
      } else if (event.type === 'agent_complete') {
        updateAgent(event.agent?.name || event.agent, {
          state: 'complete',
          result: event.result ?? event.agent?.result,
          confidence: formatConfidence(event.confidence ?? event.agent?.confidence),
          model: event.model || event.model_used || event.agent?.model,
          status: event.status || event.agent?.status,
          detail: event.detail || event.agent?.detail || '',
        });
      }
    };

    const finishJob = () => {
      if (pendingFailedError) {
        setIsFailed(true);
        setError(pendingFailedError);
        pendingFailedError = null;
        return;
      }
      if (pendingCompleteInvoice) {
        setFinalInvoice(pendingCompleteInvoice);
        setIsComplete(true);
        pendingCompleteInvoice = null;
      }
    };

    const drainQueue = () => {
      if (!active) return;

      if (eventQueue.length === 0) {
        stepTimer = null;
        if (finished) finishJob();
        return;
      }

      const event = eventQueue.shift();

      if (event.type === 'job_complete') {
        pendingCompleteInvoice = event.invoice;
        finished = true;
      } else if (event.type === 'job_failed') {
        pendingFailedError = event.error || 'Processing failed';
        finished = true;
      } else {
        applyEvent(event);
      }

      stepTimer = setTimeout(drainQueue, STEP_MS);
    };

    const enqueueEvent = (event) => {
      eventQueue.push(event);
      if (event.type === 'job_complete' || event.type === 'job_failed') {
        terminalEnqueued = true;
      }
      if (!stepTimer) drainQueue();
    };

    const enqueueFromInvoice = (invoice) => {
      for (const agent of invoice.agents || []) {
        eventQueue.push({ type: 'agent_start', agent: agent.agent });
        eventQueue.push({
          type: 'agent_complete',
          agent: agent.agent,
          result: agent.result,
          confidence: agent.confidence,
          model: agent.model,
          status: agent.status,
          detail: agent.detail,
        });
      }
      eventQueue.push({ type: 'job_complete', invoice });
      if (!stepTimer) drainQueue();
    };

    const startPolling = () => {
      if (pollTimer || finished) return;
      pollTimer = setInterval(async () => {
        const { data, error: pollError } = await getJobStatus(jobId);
        if (!active) return;

        if (pollError) {
          setError(pollError);
          return;
        }

        if (data?.status === 'complete') {
          stopPolling();
          let invoice = data.invoice;
          if (!invoice && data.invoiceId) {
            const detail = await getInvoice(data.invoiceId);
            invoice = detail.data;
          }
          if (invoice) {
            finished = true;
            enqueueFromInvoice(invoice);
          }
        } else if (data?.status === 'failed') {
          finished = true;
          stopPolling();
          setIsFailed(true);
          setError(data.error || 'Processing failed');
        }
      }, 2000);
    };

    const token = localStorage.getItem('paycrew_token');
    const wsUrl = `${import.meta.env.VITE_WS_URL}?token=${token}`;

    try {
      ws = new WebSocket(wsUrl);
    } catch {
      startPolling();
      return () => {
        active = false;
        stopPolling();
        stopStepTimer();
      };
    }

    ws.onopen = () => {
      if (active) ws.send(JSON.stringify({ jobId }));
    };

    ws.onmessage = (msg) => {
      if (!active) return;
      try {
        const event = JSON.parse(msg.data);
        enqueueEvent(event);
        if (event.type === 'job_complete' || event.type === 'job_failed') {
          ws.close(1000);
        }
      } catch {
        /* ignore */
      }
    };

    ws.onerror = () => {
      if (active && !terminalEnqueued) startPolling();
    };

    ws.onclose = () => {
      if (active && !terminalEnqueued) startPolling();
    };

    return () => {
      active = false;
      stopPolling();
      stopStepTimer();
      eventQueue.length = 0;
      if (ws) {
        ws.onopen = null;
        ws.onmessage = null;
        ws.onerror = null;
        ws.onclose = null;
        ws.close();
        ws = null;
      }
    };
  }, [jobId, enabled, reset, updateAgent]);

  return { agents, finalInvoice, isComplete, isFailed, error, reset };
}

export default useAgentTrace;
