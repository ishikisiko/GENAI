import type { ComponentProps } from "react";
import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  PButton, PText, PHeading, PSpinner, PInlineNotification,
  PTag, PDivider, PIcon,
} from "@porsche-design-system/components-react";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { getErrorMessage } from "../lib/errors";
import { supabase } from "../lib/supabase";
import { fetchJobStatus, fetchSimulationRunStatus, submitSimulation } from "../lib/backend";
import type {
  AgentResponse,
  CrisisCase,
  AgentProfile,
  JobStatusResponse,
  SimulationRun,
  SimulationRunStatusResponse,
  RoundState,
  StrategySequenceStep,
  StrategyType,
} from "../lib/types";
import { AGENT_ROLE_LABELS, AGENT_ROLE_COLORS, STRATEGY_LABELS, STRATEGY_DESCRIPTIONS, STRATEGY_ICONS } from "../lib/constants";
import { useI18n } from "../lib/i18n";

type IconName = NonNullable<ComponentProps<typeof PIcon>["name"]>;

function AgentCard({ agent }: { agent: AgentProfile }) {
  const colors = AGENT_ROLE_COLORS[agent.role];
  const roleIcons: Record<AgentProfile["role"], IconName> = {
    consumer: "user", supporter: "heart", critic: "dislike", media: "broadcast",
  };
  return (
    <div className="bg-surface border border-contrast-low rounded-lg p-fluid-sm">
      <div className="flex items-center gap-static-sm mb-static-sm">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${colors.bg}`}>
          <PIcon name={roleIcons[agent.role]} size="small" />
        </div>
        <div>
          <PText size="small" weight="semi-bold">{AGENT_ROLE_LABELS[agent.role]}</PText>
          <PText size="small" className="text-contrast-medium">{agent.stance}</PText>
        </div>
      </div>
      <PText size="small" className="text-contrast-medium mb-static-sm">{agent.persona_description}</PText>
      <div className="flex gap-static-sm">
        <div className="flex-1 bg-canvas rounded p-static-xs text-center">
          <PText size="small" className="text-contrast-medium" style={{ fontSize: "11px" }}>Sensitivity</PText>
          <PText size="small" weight="semi-bold">{agent.emotional_sensitivity}/10</PText>
        </div>
        <div className="flex-1 bg-canvas rounded p-static-xs text-center">
          <PText size="small" className="text-contrast-medium" style={{ fontSize: "11px" }}>Spread</PText>
          <PText size="small" weight="semi-bold">{agent.spread_tendency}/10</PText>
        </div>
      </div>
    </div>
  );
}

function SentimentBar({ value }: { value: number }) {
  const pct = ((value + 1) / 2) * 100;
  const color = value > 0.2 ? "bg-success" : value < -0.2 ? "bg-error" : "bg-warning";
  return (
    <div className="flex items-center gap-static-sm">
      <div className="flex-1 h-2 bg-contrast-low rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <PText size="small" className={value > 0.2 ? "text-success" : value < -0.2 ? "text-error" : "text-warning"} style={{ fontSize: "11px" }}>
        {value.toFixed(2)}
      </PText>
    </div>
  );
}

const ROLE_ICONS: Record<AgentProfile["role"], IconName> = {
  consumer: "user", supporter: "heart", critic: "dislike", media: "broadcast",
};

const STRATEGY_TYPES: StrategyType[] = ["apology", "clarification", "compensation", "rebuttal"];

type InterventionMode = "single" | "sequence";
type StrategySequenceDraftStep = {
  round_number: number;
  strategy_type: StrategyType | "";
  strategy_message: string;
};

function buildSequenceDraft(totalRounds: number, existing: StrategySequenceDraftStep[] = []): StrategySequenceDraftStep[] {
  return Array.from({ length: totalRounds }, (_, index) => {
    const roundNumber = index + 1;
    const existingStep = existing.find((step) => step.round_number === roundNumber);
    if (existingStep) return existingStep;
    return {
      round_number: roundNumber,
      strategy_type: roundNumber === 1 ? "clarification" : "",
      strategy_message: "",
    };
  });
}

function toStrategySequence(steps: StrategySequenceDraftStep[]): StrategySequenceStep[] {
  return steps
    .filter((step): step is StrategySequenceDraftStep & { strategy_type: StrategyType } => step.strategy_type !== "")
    .map((step) => ({
      round_number: step.round_number,
      strategy_type: step.strategy_type,
      strategy_message: step.strategy_message.trim() || undefined,
    }));
}

function isActiveRun(run: SimulationRun) {
  return run.status === "pending" || run.status === "running";
}

export default function SimulationPage() {
  const { t } = useI18n();
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();

  const [crisisCase, setCrisisCase] = useState<CrisisCase | null>(null);
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [runs, setRuns] = useState<SimulationRun[]>([]);
  const [roundStates, setRoundStates] = useState<Record<string, RoundState[]>>({});
  const [loading, setLoading] = useState(true);
  const [runningBaseline, setRunningBaseline] = useState(false);
  const [runningIntervention, setRunningIntervention] = useState(false);
  const [error, setError] = useState("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [runStatus, setRunStatus] = useState<SimulationRunStatusResponse | null>(null);

  const [strategyType, setStrategyType] = useState<StrategyType>("apology");
  const [strategyMessage, setStrategyMessage] = useState("");
  const [injectionRound, setInjectionRound] = useState(2);
  const [baselineTotalRounds, setBaselineTotalRounds] = useState(5);
  const [interventionTotalRounds, setInterventionTotalRounds] = useState(5);
  const [interventionMode, setInterventionMode] = useState<InterventionMode>("single");
  const [strategySequence, setStrategySequence] = useState<StrategySequenceDraftStep[]>(() => buildSequenceDraft(5));

  const fetchPageData = useCallback(async () => {
    const [{ data: c }, { data: ags }, { data: rs }] = await Promise.all([
      supabase.from("crisis_cases").select("*").eq("id", caseId!).maybeSingle(),
      supabase.from("agent_profiles").select("*").eq("case_id", caseId!),
      supabase.from("simulation_runs").select("*").eq("case_id", caseId!).order("created_at"),
    ]);
    const runsData = rs ?? [];
    const activeRun = [...runsData].reverse().find((run) => isActiveRun(run) && run.job_id);

    const runStates: Record<string, RoundState[]> = {};
    for (const run of runsData) {
      if (run.status === "completed") {
        const { data: states } = await supabase
          .from("round_states")
          .select("*")
          .eq("run_id", run.id)
          .order("round_number");
        runStates[run.id] = states ?? [];
      }
    }

    return {
      crisisCase: c,
      agents: ags ?? [],
      runsData,
      activeRun,
      runStates,
    };
  }, [caseId]);

  const load = useCallback(async () => {
    setLoading(true);
    const data = await fetchPageData();
    setCrisisCase(data.crisisCase);
    setAgents(data.agents);
    setRuns(data.runsData);
    setActiveRunId(data.activeRun?.id ?? null);
    setActiveJobId(data.activeRun?.job_id ?? null);
    if (!data.activeRun) {
      setJobStatus(null);
      setRunStatus(null);
    }
    setRoundStates(data.runStates);
    setLoading(false);
  }, [fetchPageData]);

  useEffect(() => {
    if (!caseId) return undefined;
    let cancelled = false;

    async function runInitialLoad() {
      const data = await fetchPageData();
      if (cancelled) return;
      setCrisisCase(data.crisisCase);
      setAgents(data.agents);
      setRuns(data.runsData);
      setActiveRunId(data.activeRun?.id ?? null);
      setActiveJobId(data.activeRun?.job_id ?? null);
      if (!data.activeRun) {
        setJobStatus(null);
        setRunStatus(null);
      }
      setRoundStates(data.runStates);
      setLoading(false);
    }

    void runInitialLoad();

    return () => {
      cancelled = true;
    };
  }, [caseId, fetchPageData]);

  const effectiveInjectionRound = Math.min(injectionRound, interventionTotalRounds);

  useEffect(() => {
    if (!activeJobId || !activeRunId) return undefined;

    const jobId = activeJobId;
    const runId = activeRunId;
    const jobStatusPath = jobStatus?.job_status_path || jobId;
    const runStatusPath = runStatus?.status_path || runId;
    let cancelled = false;
    let timeoutId: number | undefined;

    async function pollStatus() {
      try {
        const [nextJobStatus, nextRunStatus] = await Promise.all([
          fetchJobStatus(jobStatusPath),
          fetchSimulationRunStatus(runStatusPath),
        ]);

        if (cancelled) return;
        setJobStatus(nextJobStatus);
        setRunStatus(nextRunStatus);

        if (!nextRunStatus.should_poll) {
          setActiveJobId(null);
          setActiveRunId(null);
          await load();
          return;
        }

        timeoutId = window.setTimeout(() => {
          void pollStatus();
        }, 2000);
      } catch (pollError: unknown) {
        if (cancelled) return;
        setError(getErrorMessage(pollError, "Failed to poll simulation status."));
      }
    }

    void pollStatus();

    return () => {
      cancelled = true;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [activeJobId, activeRunId, jobStatus?.job_status_path, load, runStatus?.status_path]);

  async function runSimulation(type: "baseline" | "intervention") {
    setError("");
    if (type === "baseline") setRunningBaseline(true);
    else setRunningIntervention(true);

    try {
      const sequencePayload = type === "intervention" && interventionMode === "sequence"
        ? toStrategySequence(strategySequence)
        : [];
      if (type === "intervention" && interventionMode === "sequence" && sequencePayload.length === 0) {
        throw new Error("Add at least one strategy step before running a sequence intervention.");
      }

      const result = await submitSimulation({
        case_id: caseId!,
        run_type: type,
        total_rounds: type === "baseline" ? baselineTotalRounds : interventionTotalRounds,
        ...(type === "intervention" && interventionMode === "single" && {
          strategy_type: strategyType,
          strategy_message: strategyMessage || undefined,
          injection_round: effectiveInjectionRound,
        }),
        ...(type === "intervention" && interventionMode === "sequence" && {
          strategy_sequence: sequencePayload,
        }),
      });

      setActiveJobId(result.job_id);
      setActiveRunId(result.run_id);
      setJobStatus({
        outcome: "status",
        id: result.job_id,
        job_id: result.job_id,
        job_type: result.job_type,
        status: result.job_status,
        job_status_path: result.job_status_path,
        status_path: result.status_path,
        run_id: result.run_id,
        last_error: null,
        last_error_code: null,
        locked_at: null,
        heartbeat_at: null,
        updated_at: null,
        created_at: null,
        should_poll: result.should_poll,
      });
      setRunStatus({
        outcome: "status",
        id: result.run_id,
        job_type: "simulation.run",
        job_id: result.job_id,
        status: result.run_status,
        job_status_path: result.job_status_path,
        status_path: result.status_path,
        error_message: null,
        total_rounds: type === "baseline" ? baselineTotalRounds : interventionTotalRounds,
        completed_rounds: 0,
        last_completed_round: 0,
        last_heartbeat_at: null,
        created_at: new Date().toISOString(),
        completed_at: null,
        should_poll: result.should_poll,
      });
      await load();
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Simulation failed."));
    }

    setRunningBaseline(false);
    setRunningIntervention(false);
  }

  

  const baselineRun = runs.find((r) => r.run_type === "baseline" && r.status === "completed");
  const hasBaseline = !!baselineRun;
  const hasRunningSim = runs.some((r) => isActiveRun(r));
  const runningProgress =
    runStatus && activeRunId
      ? `${runStatus.completed_rounds}/${runStatus.total_rounds} rounds complete`
      : null;
  const activeJobSummary = jobStatus ? `job ${jobStatus.status}` : null;

  if (loading) return (
    <div className="flex items-center justify-center min-h-full"><PSpinner size="medium" /></div>
  );

  return (
    <div className="min-h-full">
      <PageHeader
        title={t("simulation.title")}
        subtitle={crisisCase?.title}
        breadcrumbs={[{ label: t("common.dashboard"), href: "/" }, { label: crisisCase?.title || t("common.case") }, { label: t("nav.simulation") }]}
        action={
          <div className="flex items-center gap-static-sm">
            {crisisCase && <StatusBadge status={crisisCase.status} />}
            {hasBaseline && (
              <PButton icon="compare" variant="secondary" onClick={() => navigate(`/cases/${caseId}/comparison`)}>
                {t("simulation.viewComparison")}
              </PButton>
            )}
          </div>
        }
      />

      <div className="w-full p-fluid-lg">
        {error && (
          <PInlineNotification heading={t("common.error")} description={error} state="error" dismissButton className="mb-fluid-md" onDismiss={() => setError("")} />
        )}

        {agents.length === 0 ? (
          <div className="bg-surface border border-contrast-low rounded-lg p-fluid-xl flex flex-col items-center gap-static-md text-center">
            <PIcon name="group" size="large" color="contrast-medium" />
            <PText className="text-contrast-medium">No agents yet. Go back and generate agents from the grounding results.</PText>
            <PButton variant="secondary" icon="arrow-left" onClick={() => navigate(`/cases/${caseId}/grounding`)}>
              Back to Grounding
            </PButton>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-fluid-md xl:grid-cols-[minmax(28rem,0.9fr)_minmax(0,1.55fr)] 2xl:grid-cols-[minmax(34rem,0.85fr)_minmax(0,1.75fr)]">
            <div className="flex flex-col gap-fluid-md">
              <div>
                <PHeading size="small" className="mb-fluid-sm">{t("simulation.stakeholderAgents")}</PHeading>
                <div className="grid grid-cols-1 gap-static-sm md:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
                  {agents.map((a) => <AgentCard key={a.id} agent={a} />)}
                </div>
              </div>

              <PDivider />

              <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md flex flex-col gap-fluid-sm">
                <PHeading size="small">{t("simulation.runBaseline")}</PHeading>
                <PText size="small" className="text-contrast-medium">
                  Simulate {baselineTotalRounds} rounds with no intervention — establishes the natural crisis trajectory.
                </PText>
                <div>
                  <PText size="small" weight="semi-bold" className="mb-static-xs">Final Round</PText>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={baselineTotalRounds}
                    onChange={(e) => {
                      const next = Number(e.target.value);
                      if (Number.isFinite(next)) {
                        setBaselineTotalRounds(Math.min(Math.max(next, 1), 20));
                      }
                    }}
                    className="w-full border border-contrast-low rounded bg-canvas px-static-sm py-static-xs text-primary focus:outline-none focus:border-primary text-sm"
                    style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
                  />
                </div>
                <PButton
                  loading={runningBaseline}
                  disabled={runningBaseline || runningIntervention || hasRunningSim || !agents.length}
                  icon="chart"
                  onClick={() => runSimulation("baseline")}
                >
                  {runningBaseline
                    ? "Simulating..."
                    : hasRunningSim
                      ? "Run baseline later"
                      : hasBaseline
                        ? "Re-run Baseline"
                        : "Run Baseline"}
                </PButton>
                {hasRunningSim && (
                  <PText size="small" className="text-warning text-center">
                    A simulation is currently running for this case. Wait for completion before starting another.
                  </PText>
                )}
                {runningBaseline && (
                  <PText size="small" className="text-contrast-medium text-center">
                    Submitting baseline simulation...
                  </PText>
                )}
              </div>

              <div className="bg-surface border border-notification-warning rounded-lg p-fluid-md flex flex-col gap-fluid-sm">
                <PHeading size="small">{t("simulation.injectStrategy")}</PHeading>

                <div>
                  <PText size="small" weight="semi-bold" className="mb-static-xs">Intervention Mode</PText>
                  <div className="grid grid-cols-2 gap-static-xs">
                    {(["single", "sequence"] as InterventionMode[]).map((mode) => (
                      <button
                        key={mode}
                        onClick={() => setInterventionMode(mode)}
                        className={`px-static-sm py-static-sm rounded border text-sm font-medium transition-colors ${
                          interventionMode === mode
                            ? "border-primary bg-primary text-[white]"
                            : "border-contrast-low bg-canvas text-contrast-medium hover:border-primary"
                        }`}
                        style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
                      >
                        {mode === "single" ? "Single Strategy" : "Strategy Sequence"}
                      </button>
                    ))}
                  </div>
                </div>

                {interventionMode === "single" && (
                <div>
                  <PText size="small" weight="semi-bold" className="mb-static-xs">Strategy Type</PText>
                  <div className="grid grid-cols-1 gap-static-xs sm:grid-cols-2">
                    {STRATEGY_TYPES.map((s) => (
                      <button
                        key={s}
                        onClick={() => setStrategyType(s)}
                        className={`flex items-center gap-static-xs p-static-sm rounded border text-left transition-colors ${
                          strategyType === s
                            ? "border-primary bg-primary text-[white]"
                            : "border-contrast-low bg-canvas text-contrast-medium hover:border-primary"
                        }`}
                        style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
                      >
                        <PIcon name={STRATEGY_ICONS[s] as IconName} size="small" color="inherit" />
                        <PText size="small" style={{ color: "inherit" }}>{STRATEGY_LABELS[s]}</PText>
                      </button>
                    ))}
                  </div>
                  <PText size="small" className="text-contrast-medium mt-static-xs">
                    {STRATEGY_DESCRIPTIONS[strategyType]}
                  </PText>
                </div>
                )}

                <div>
                  <PText size="small" weight="semi-bold" className="mb-static-xs">Final Round</PText>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={interventionTotalRounds}
                    onChange={(e) => {
                      const next = Number(e.target.value);
                      if (Number.isFinite(next)) {
                        const clamped = Math.min(Math.max(next, 1), 20);
                        setInterventionTotalRounds(clamped);
                        setInjectionRound((current) => Math.min(current, clamped));
                        setStrategySequence((current) => buildSequenceDraft(clamped, current));
                      }
                    }}
                    className="w-full border border-contrast-low rounded bg-canvas px-static-sm py-static-xs text-primary focus:outline-none focus:border-primary text-sm"
                    style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
                  />
                  <PText size="small" className="text-contrast-medium mt-static-xs">
                    Intervention simulation will stop after round {interventionTotalRounds}
                  </PText>
                </div>

                {interventionMode === "single" && (
                <div>
                  <PText size="small" weight="semi-bold" className="mb-static-xs">
                    Inject at Round
                  </PText>
                  <div className="flex flex-wrap gap-static-xs">
                    {Array.from({ length: interventionTotalRounds }, (_, index) => index + 1).map((r) => (
                      <button
                        key={r}
                        onClick={() => setInjectionRound(r)}
                        className={`w-9 h-9 rounded border text-sm font-medium transition-colors ${
                          effectiveInjectionRound === r
                            ? "border-primary bg-primary text-[white]"
                            : "border-contrast-low bg-canvas text-contrast-medium hover:border-primary"
                        }`}
                        style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                  <PText size="small" className="text-contrast-medium mt-static-xs">
                    Strategy applied at the start of round {effectiveInjectionRound}
                  </PText>
                </div>
                )}

                {interventionMode === "single" && (
                <div>
                  <PText size="small" weight="semi-bold" className="mb-static-xs">Custom Message (optional)</PText>
                  <textarea
                    value={strategyMessage}
                    onChange={(e) => setStrategyMessage(e.target.value)}
                    placeholder={`Leave blank to use default ${STRATEGY_LABELS[strategyType].toLowerCase()} message...`}
                    rows={3}
                    className="w-full border border-contrast-low rounded bg-canvas px-static-sm py-static-xs text-primary placeholder:text-contrast-low focus:outline-none focus:border-primary resize-none text-sm"
                    style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
                  />
                </div>
                )}

                {interventionMode === "sequence" && (
                  <div className="flex flex-col gap-static-sm">
                    <div className="flex items-center justify-between gap-static-sm">
                      <PText size="small" weight="semi-bold">Per-Round Plan</PText>
                      <PTag color="notification-info-soft">
                        {toStrategySequence(strategySequence).length} planned
                      </PTag>
                    </div>
                    {strategySequence.map((step) => (
                      <div key={step.round_number} className="bg-canvas border border-contrast-low rounded p-static-sm flex flex-col gap-static-xs">
                        <div className="flex flex-col gap-static-xs sm:flex-row sm:items-center">
                          <PText size="small" weight="semi-bold" className="sm:w-20">Round {step.round_number}</PText>
                          <select
                            value={step.strategy_type}
                            onChange={(e) => {
                              const nextStrategy = e.target.value as StrategyType | "";
                              setStrategySequence((current) => current.map((currentStep) => (
                                currentStep.round_number === step.round_number
                                  ? { ...currentStep, strategy_type: nextStrategy }
                                  : currentStep
                              )));
                            }}
                            className="flex-1 border border-contrast-low rounded bg-surface px-static-sm py-static-xs text-primary focus:outline-none focus:border-primary text-sm"
                            style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
                          >
                            <option value="">No intervention</option>
                            {STRATEGY_TYPES.map((strategy) => (
                              <option key={strategy} value={strategy}>{STRATEGY_LABELS[strategy]}</option>
                            ))}
                          </select>
                        </div>
                        {step.strategy_type && (
                          <textarea
                            value={step.strategy_message}
                            onChange={(e) => {
                              const nextMessage = e.target.value;
                              setStrategySequence((current) => current.map((currentStep) => (
                                currentStep.round_number === step.round_number
                                  ? { ...currentStep, strategy_message: nextMessage }
                                  : currentStep
                              )));
                            }}
                            placeholder={`Optional ${STRATEGY_LABELS[step.strategy_type].toLowerCase()} message for round ${step.round_number}...`}
                            rows={2}
                            className="w-full border border-contrast-low rounded bg-surface px-static-sm py-static-xs text-primary placeholder:text-contrast-low focus:outline-none focus:border-primary resize-none text-sm"
                            style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                )}

                  <PButton
                    loading={runningIntervention}
                    disabled={runningBaseline || runningIntervention || !hasBaseline || hasRunningSim}
                    icon="arrow-right"
                    variant="secondary"
                    onClick={() => runSimulation("intervention")}
                >
                  {runningIntervention
                    ? "Simulating..."
                    : hasRunningSim
                      ? "Run later"
                      : interventionMode === "sequence"
                        ? "Run Strategy Sequence"
                        : "Run Intervention"}
                </PButton>
                {!hasBaseline && (
                  <PText size="small" className="text-warning text-center">Run baseline first</PText>
                )}
                {hasRunningSim && (
                  <PText size="small" className="text-warning text-center">
                    A simulation is currently running for this case. Wait for completion before starting another.
                  </PText>
                )}
              </div>
            </div>

            <div className="min-w-0 flex flex-col gap-fluid-md">
              <PHeading size="small">{t("simulation.logs")}</PHeading>

              {runs.length === 0 && !runningBaseline && !runningIntervention ? (
                <div className="bg-surface border border-contrast-low rounded-lg p-fluid-lg flex flex-col items-center gap-static-md text-center">
                  <PIcon name="chart" size="large" color="contrast-medium" />
                  <PText className="text-contrast-medium">No simulations run yet. Start with the baseline.</PText>
                </div>
              ) : (
                <div className="flex flex-col gap-fluid-sm">
                  {(runningBaseline || runningIntervention) && (
                    <div className="bg-notification-info-soft border border-notification-info rounded-lg p-fluid-md flex items-center gap-static-md">
                      <PSpinner size="small" />
                      <div>
                        <PText size="small" weight="semi-bold">
                          {runningBaseline
                            ? "Submitting Baseline Simulation..."
                            : interventionMode === "sequence"
                              ? "Submitting Strategy Sequence..."
                              : `Submitting ${STRATEGY_LABELS[strategyType]} Intervention...`}
                        </PText>
                        <PText size="small" className="text-contrast-medium">
                          The worker will pick up the job and the page will poll lightweight status endpoints until the run finishes.
                        </PText>
                      </div>
                    </div>
                  )}

                  {[...runs].reverse().map((run) => {
                    const states = roundStates[run.id] || [];
                    const isRunning = isActiveRun(run);
                    const isTrackedActiveRun = run.id === activeRunId && runStatus;
                    const sequence = run.strategy_sequence ?? [];
                    return (
                      <div key={run.id} className="bg-surface border border-contrast-low rounded-lg overflow-hidden">
                        <div className="flex flex-col gap-static-sm px-fluid-sm py-static-md border-b border-contrast-low lg:flex-row lg:items-center lg:justify-between">
                          <div className="flex flex-wrap items-center gap-static-sm">
                            <PTag color={run.run_type === "baseline" ? "background-frosted" : "notification-warning-soft"}>
                              {run.run_type === "baseline" ? "Baseline" : "Intervention"}
                            </PTag>
                            {sequence.length > 0 && (
                              <PTag color="notification-info-soft">Sequence: {sequence.length} steps</PTag>
                            )}
                            {sequence.length === 0 && run.strategy_type && (
                              <PTag color="notification-info-soft">{STRATEGY_LABELS[run.strategy_type as StrategyType]}</PTag>
                            )}
                            {sequence.length === 0 && run.injection_round && (
                              <PText size="small" className="text-contrast-medium">@ Round {run.injection_round}</PText>
                            )}
                          </div>
                          <div className="flex flex-wrap items-center gap-static-sm">
                            <PTag color={run.status === "completed" ? "notification-success-soft" : run.status === "failed" ? "notification-error-soft" : "background-frosted"}>
                              {run.status}
                            </PTag>
                            <PText size="small" className="text-contrast-low">
                              {new Date(run.created_at).toLocaleString()}
                            </PText>
                          </div>
                        </div>

                        {isRunning && (
                          <div className="p-fluid-sm flex items-center gap-static-sm">
                            <PSpinner size="small" />
                            <PText size="small" className="text-contrast-medium">
                              {run.status === "pending"
                                ? activeJobSummary
                                  ? `Queued for worker execution... (${activeJobSummary})`
                                  : "Queued for worker execution..."
                                : isTrackedActiveRun && runningProgress
                                  ? `Running simulation rounds... ${runningProgress}`
                                  : "Running simulation rounds..."}
                            </PText>
                          </div>
                        )}

                        {!isRunning && run.status === "failed" && run.error_message && (
                          <div className="px-fluid-sm py-static-md border-b border-contrast-low bg-notification-error-soft">
                            <PText size="small" className="text-error">{run.error_message}</PText>
                          </div>
                        )}

                        {states.length > 0 && (
                          <div className="divide-y divide-contrast-low">
                            {states.map((state) => (
                              <div key={state.id} className="p-fluid-sm">
                                <div className="flex flex-col gap-static-sm mb-static-sm lg:flex-row lg:items-center lg:justify-between">
                                  <div className="flex flex-wrap items-center gap-static-sm">
                                    <PText size="small" weight="semi-bold" className="text-primary">
                                      Round {state.round_number}
                                    </PText>
                                    {state.strategy_applied && (
                                      <PTag color="notification-warning-soft">{STRATEGY_LABELS[state.strategy_applied as StrategyType]} applied</PTag>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-static-sm w-full sm:w-48 lg:w-32">
                                    <PText size="small" className="text-contrast-medium shrink-0" style={{ fontSize: "11px" }}>Sentiment</PText>
                                    <SentimentBar value={state.overall_sentiment} />
                                  </div>
                                </div>

                                <PText size="small" className="text-contrast-medium mb-static-sm italic">
                                  {state.narrative_state}
                                </PText>

                                <div className="flex flex-col gap-static-xs">
                                  {state.agent_responses.map((resp: AgentResponse, i: number) => {
                                    const colors = AGENT_ROLE_COLORS[resp.role] || AGENT_ROLE_COLORS.consumer;
                                    return (
                                      <div key={i} className="flex gap-static-sm">
                                        <div className={`w-6 h-6 shrink-0 rounded-full flex items-center justify-center mt-0.5 ${colors.bg}`}>
                                          <PIcon name={ROLE_ICONS[resp.role] || "user"} size="small" />
                                        </div>
                                        <div className="flex-1">
                                          <PText size="small" weight="semi-bold" className={colors.text} style={{ fontSize: "11px" }}>
                                            {AGENT_ROLE_LABELS[resp.role as keyof typeof AGENT_ROLE_LABELS] || resp.role}
                                          </PText>
                                          <PText size="small" className="text-contrast-high">{resp.response}</PText>
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
