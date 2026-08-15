import { Link } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';

function PayCrewLogo({ className = '' }) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <svg className="h-5 w-5 text-primary" fill="currentColor" viewBox="0 0 24 24">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
      </svg>
      <span className="text-lg font-bold text-primary">PayCrew</span>
    </div>
  );
}

const problems = [
  {
    icon: (
      <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    title: "It's slow",
    body: 'AP teams spend 60% of their time on routine checks that add zero value.',
  },
  {
    icon: (
      <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    title: "It's error-prone",
    body: 'Duplicate payments and fake vendors cost companies 5% of annual spend.',
  },
  {
    icon: (
      <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    title: "It's expensive",
    body: '$15 to process a single invoice manually. At 500/month that\'s $7,500 gone.',
  },
];

const flowSteps = [
  { label: 'Parse', icon: '📄' },
  { label: 'Match PO', icon: '🔗' },
  { label: 'Check Duplicate', icon: '🔍' },
  { label: 'Fraud Signal', icon: '🛡️' },
  { label: 'Risk Score', icon: '📊' },
  { label: 'Route', icon: '→' },
];

function FlowPill({ label, icon, lit }) {
  return (
    <div
      className={`flow-pill flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-xs sm:gap-2 sm:px-4 sm:py-2 sm:text-sm ${lit ? 'flow-pill-lit' : ''}`}
    >
      <span className="text-sm leading-none sm:text-base">{icon}</span>
      <span className="whitespace-nowrap">{label}</span>
    </div>
  );
}

function FlowLineRight({ lit }) {
  return (
    <div className={`flow-line flex shrink-0 items-center px-1 sm:px-2 ${lit ? 'flow-line-lit' : ''}`}>
      <div className="h-px w-4 bg-current sm:w-6 md:w-10" />
      <svg className="h-3 w-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </div>
  );
}

function FlowRow({ steps, activeStep, startIndex }) {
  return (
    <div className="flex items-center justify-center">
      {steps.map((step, i) => {
        const idx = startIndex + i;
        return (
          <div key={step.label} className="flex items-center">
            <FlowPill label={step.label} icon={step.icon} lit={activeStep >= idx} />
            {i < steps.length - 1 && (
              <FlowLineRight lit={activeStep >= idx + 1} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function AgentFlowDiagram({ activeStep }) {
  const row1 = flowSteps.slice(0, 3);
  const row2 = flowSteps.slice(3, 6);

  return (
    <>
      {/* Desktop: one continuous left-to-right line */}
      <div className="mx-auto hidden max-w-5xl lg:block">
        <FlowRow steps={flowSteps} activeStep={activeStep} startIndex={0} />
      </div>

      {/* Mobile / tablet: two horizontal lines */}
      <div className="mx-auto w-full max-w-3xl space-y-5 sm:space-y-6 lg:hidden">
        <FlowRow steps={row1} activeStep={activeStep} startIndex={0} />
        <FlowRow steps={row2} activeStep={activeStep} startIndex={3} />
      </div>
    </>
  );
}

const roiStats = [
  { value: '98%', label: 'invoices auto-processed' },
  { value: '$0.004', label: 'cost per invoice analysis' },
  { value: '< 15s', label: 'end to end processing time' },
];

export default function Landing() {
  const solutionRef = useRef(null);
  const timeoutsRef = useRef([]);
  const [flowVisible, setFlowVisible] = useState(false);
  const [activeStep, setActiveStep] = useState(-1);

  const startFlow = () => {
    timeoutsRef.current.forEach(clearTimeout);
    timeoutsRef.current = [];
    setActiveStep(-1);
    setFlowVisible(true);

    flowSteps.forEach((_, i) => {
      const t = setTimeout(() => setActiveStep(i), i * 450);
      timeoutsRef.current.push(t);
    });
  };

  const resetFlow = () => {
    timeoutsRef.current.forEach(clearTimeout);
    timeoutsRef.current = [];
    setFlowVisible(false);
    setActiveStep(-1);
  };

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          startFlow();
        } else {
          resetFlow();
        }
      },
      { threshold: 0.3 }
    );
    if (solutionRef.current) observer.observe(solutionRef.current);
    return () => {
      observer.disconnect();
      timeoutsRef.current.forEach(clearTimeout);
    };
  }, []);

  const scrollToSolution = () => {
    document.getElementById('solution')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="ambient-bg page-enter">
      {/* Hero */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <PayCrewLogo />
        <Link
          to="/login"
          className="rounded-lg border border-primary px-4 py-2 text-sm text-primary transition-default hover:bg-primary/10"
        >
          Login
        </Link>
      </header>

      <section className="mx-auto max-w-4xl px-6 py-20 text-center">
        <h1 className="text-4xl font-semibold tracking-tight text-text-primary md:text-5xl">
          Your AI finance team.
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-text-secondary">
          500 invoices a month. 3 that need your attention. We find them.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <span className="rounded-full border border-border bg-surface px-4 py-1.5 text-xs text-text-secondary">
            ⚡ Processes in seconds
          </span>
          <span className="rounded-full border border-border bg-surface px-4 py-1.5 text-xs text-text-secondary">
            🔒 Full audit trail
          </span>
        </div>
        <button
          onClick={scrollToSolution}
          className="mt-10 rounded-lg bg-primary px-6 py-3 text-sm font-medium text-white transition-default hover:bg-primary/90"
        >
          See it in action →
        </button>
      </section>

      {/* Problem */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <p className="text-xs font-medium uppercase tracking-widest text-primary">The Problem</p>
        <h2 className="mt-2 text-2xl font-semibold text-text-primary md:text-3xl">
          Manual invoice processing is broken.
        </h2>
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {problems.map((p) => (
            <div key={p.title} className="card-hover rounded-xl border border-border bg-surface p-6">
              <div className="mb-4 text-primary">{p.icon}</div>
              <h3 className="font-semibold text-text-primary">{p.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-text-secondary">{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Solution */}
      <section id="solution" ref={solutionRef} className="mx-auto max-w-6xl px-6 py-16">
        <p className="text-xs font-medium uppercase tracking-widest text-primary">The Solution</p>
        <h2 className="mt-2 text-2xl font-semibold text-text-primary md:text-3xl">
          Six AI agents. One decision.
        </h2>

        <div className={`flow-diagram mt-12 ${flowVisible ? 'flow-visible' : ''}`}>
          <AgentFlowDiagram activeStep={activeStep} />
        </div>

        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {roiStats.map((stat) => (
            <div key={stat.label} className="text-center">
              <p className="text-3xl font-semibold text-primary md:text-4xl">{stat.value}</p>
              <p className="mt-2 text-sm text-text-muted">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="mx-auto max-w-6xl px-6 py-16 text-center">
        <p className="text-xs text-text-muted">Built with CrewAI + TrueFoundry</p>
        <Link
          to="/login"
          className="mt-6 inline-block rounded-lg border border-primary px-6 py-2.5 text-sm text-primary transition-default hover:bg-primary/10"
        >
          Login
        </Link>
      </footer>
    </div>
  );
}
