import type { ComponentProps } from "react";
import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  PButton, PText, PHeading, PSpinner, PInlineNotification,
  PTag, PIcon,
} from "@porsche-design-system/components-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { supabase } from "../lib/supabase";
import { DEMO_CASE_ID } from "../lib/seedDemo";
import type {
  AgentResponse, CrisisCase, SimulationRun, MetricSnapshot, RoundState, StrategyType,
} from "../lib/types";
import { STRATEGY_LABELS, AGENT_ROLE_LABELS, AGENT_ROLE_COLORS } from "../lib/constants";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";

type IconName = NonNullable<ComponentProps<typeof PIcon>["name"]>;

interface RunData {
  run: SimulationRun;
  metrics: MetricSnapshot[];
  rounds: RoundState[];
}

const CHART_COLORS = {
  baseline: "#535457",
  apology: "#13D246",
  clarification: "#4FB3FF",
  compensation: "#FF9F00",
  rebuttal: "#FF6240",
};

function getRunColor(run: SimulationRun) {
  if (run.run_type === "baseline") return CHART_COLORS.baseline;
  return CHART_COLORS[run.strategy_type as keyof typeof CHART_COLORS] || "#4FB3FF";
}

function getRunLabel(run: SimulationRun) {
  if (run.run_type === "baseline") return "Baseline (No Response)";
  return `${STRATEGY_LABELS[run.strategy_type as StrategyType] || run.strategy_type} @ Round ${run.injection_round}`;
}

function ScoreCard({ label, baseline, best, icon, higherIsBetter = false }: {
  label: string; baseline: number; best: number; icon: IconName; higherIsBetter?: boolean;
}) {
  const diff = best - baseline;
  const improved = higherIsBetter ? diff > 0 : diff < 0;
  const pct = baseline !== 0 ? Math.abs(diff / baseline * 100) : Math.abs(diff * 100);
  return (
    <div className="bg-surface border border-contrast-low rounded-lg p-fluid-sm">
      <div className="flex items-center gap-static-xs mb-static-sm">
        <PIcon name={icon} size="small" color="contrast-medium" />
        <PText size="small" className="text-contrast-medium">{label}</PText>
      </div>
      <div className="flex items-end gap-static-sm">
        <PHeading size="medium">{best.toFixed(2)}</PHeading>
        <PTag color={improved ? "notification-success-soft" : "notification-error-soft"}>
          {improved ? "+" : "-"} {pct.toFixed(0)}%
        </PTag>
      </div>
      <PText size="small" className="text-contrast-low mt-static-xs">vs baseline {baseline.toFixed(2)}</PText>
    </div>
  );
}

type MetricKey = "sentiment_score" | "polarization_score" | "negative_claim_spread" | "stabilization_indicator";

function buildChartData(allRuns: RunData[], metric: MetricKey): object[] {
  const maxRounds = Math.max(...allRuns.map((r) => r.metrics.length), 5);
  return Array.from({ length: maxRounds }, (_, i) => {
    const round = i + 1;
    const point: Record<string, unknown> = { round };
    for (const rd of allRuns) {
      const snap = rd.metrics.find((m) => m.round_number === round);
      if (snap) point[rd.run.id] = Number((snap[metric] as number).toFixed(3));
    }
    return point;
  });
}

function generateVerdict(baselineData: RunData, interventionRuns: RunData[]): string {
  if (interventionRuns.length === 0) return "No intervention runs to compare yet. Run at least one strategy.";

  const baselineFinalSentiment = baselineData.metrics.at(-1)?.sentiment_score ?? 0;
  const baselineFinalPolarization = baselineData.metrics.at(-1)?.polarization_score ?? 0;

  const ranked = interventionRuns
    .map((rd) => {
      const finalSentiment = rd.metrics.at(-1)?.sentiment_score ?? 0;
      const finalPolarization = rd.metrics.at(-1)?.polarization_score ?? 0;
      const finalStabilization = rd.metrics.at(-1)?.stabilization_indicator ?? 0;
      const sentimentGain = finalSentiment - baselineFinalSentiment;
      const polarizationReduction = baselineFinalPolarization - finalPolarization;
      const score = sentimentGain * 0.5 + polarizationReduction * 0.3 + finalStabilization * 0.2;
      return { rd, score, sentimentGain, polarizationReduction };
    })
    .sort((a, b) => b.score - a.score);

  const best = ranked[0];
  const stratLabel = STRATEGY_LABELS[best.rd.run.strategy_type as StrategyType] || best.rd.run.strategy_type;
  const earlyLate = (best.rd.run.injection_round ?? 0) <= 2 ? "early" : "late";

  const sentimentEffect = best.sentimentGain > 0.1 ? "meaningfully improved sentiment" : best.sentimentGain < -0.1 ? "failed to improve sentiment" : "had a neutral effect on sentiment";
  const polarizationEffect = best.polarizationReduction > 0.1 ? "significantly reduced polarization" : "had limited effect on polarization";

  let verdict = `The ${stratLabel} strategy (injected ${earlyLate}, round ${best.rd.run.injection_round}) performed best overall. `;
  verdict += `It ${sentimentEffect} and ${polarizationEffect} compared to the no-response baseline. `;

  if (ranked.length > 1) {
    const worst = ranked[ranked.length - 1];
    const worstLabel = STRATEGY_LABELS[worst.rd.run.strategy_type as StrategyType] || worst.rd.run.strategy_type;
    verdict += `The ${worstLabel} strategy performed least effectively in this scenario.`;
  }

  return verdict;
}

const ROLE_ICONS: Record<AgentResponse["role"], IconName> = {
  consumer: "user", supporter: "heart", critic: "dislike", media: "broadcast",
};

export default function ComparisonPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();

  const [crisisCase, setCrisisCase] = useState<CrisisCase | null>(null);
  const [allRuns, setAllRuns] = useState<RunData[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeMetric, setActiveMetric] = useState<MetricKey>("sentiment_score");
  const [expandedRound, setExpandedRound] = useState<string | null>(null);

  const fetchComparisonData = useCallback(async () => {
    const { data: c } = await supabase.from("crisis_cases").select("*").eq("id", caseId!).maybeSingle();

    const { data: runs } = await supabase
      .from("simulation_runs")
      .select("*")
      .eq("case_id", caseId!)
      .eq("status", "completed")
      .order("created_at");

    const runDataArray: RunData[] = [];
    for (const run of runs ?? []) {
      const [{ data: metrics }, { data: rounds }] = await Promise.all([
        supabase.from("metric_snapshots").select("*").eq("run_id", run.id).order("round_number"),
        supabase.from("round_states").select("*").eq("run_id", run.id).order("round_number"),
      ]);
      runDataArray.push({
        run,
        metrics: metrics ?? [],
        rounds: rounds ?? [],
      });
    }
    return { crisisCase: c, runDataArray };
  }, [caseId]);

  useEffect(() => {
    if (!caseId) return undefined;
    let cancelled = false;

    async function runInitialLoad() {
      const { crisisCase, runDataArray } = await fetchComparisonData();
      if (cancelled) return;
      setCrisisCase(crisisCase);
      setAllRuns(runDataArray);
      setLoading(false);
    }

    void runInitialLoad();

    return () => {
      cancelled = true;
    };
  }, [caseId, fetchComparisonData]);

  const metricTabs: { key: MetricKey; label: string; icon: IconName; higherIsBetter: boolean }[] = [
    { key: "sentiment_score", label: "Sentiment", icon: "heart", higherIsBetter: true },
    { key: "polarization_score", label: "Polarization", icon: "arrows", higherIsBetter: false },
    { key: "negative_claim_spread", label: "Claim Spread", icon: "broadcast", higherIsBetter: false },
    { key: "stabilization_indicator", label: "Stabilization", icon: "check", higherIsBetter: true },
  ];

  const baselineData = allRuns.find((r) => r.run.run_type === "baseline");
  const interventionRuns = allRuns.filter((r) => r.run.run_type === "intervention");
  const chartData = allRuns.length > 0 ? buildChartData(allRuns, activeMetric) : [];
  const activeTabCfg = metricTabs.find((t) => t.key === activeMetric)!;

  if (loading) return (
    <div className="flex items-center justify-center min-h-full"><PSpinner size="medium" /></div>
  );

  const noData = allRuns.length === 0;

  return (
    <div className="min-h-full">
      <PageHeader
        title="Strategy Comparison"
        subtitle={crisisCase?.title}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: crisisCase?.title || "Case" }, { label: "Comparison" }]}
        action={
          <div className="flex items-center gap-static-sm">
            {crisisCase && <StatusBadge status={crisisCase.status} />}
            <PButton icon="chart" variant="secondary" onClick={() => navigate(`/cases/${caseId}/simulation`)}>
              Back to Simulation
            </PButton>
          </div>
        }
      />

      <div className="p-fluid-lg max-w-6xl flex flex-col gap-fluid-md">
        {noData ? (
          <div className="bg-surface border border-contrast-low rounded-lg p-fluid-xl flex flex-col items-center gap-static-md text-center">
            <PIcon name="compare" size="large" color="contrast-medium" />
            <PHeading size="small">No completed simulations yet</PHeading>
            <PText className="text-contrast-medium max-w-md">
              Run a baseline simulation and at least one strategy intervention to see a comparison here.
            </PText>
            <PButton icon="arrow-left" onClick={() => navigate(`/cases/${caseId}/simulation`)}>
              Go to Simulation
            </PButton>
          </div>
        ) : (
          <>
            {caseId === DEMO_CASE_ID && (
              <PInlineNotification
                heading="Demo Simulation"
                description="This is a pre-loaded demo scenario — NutriPlus Protein Bar Salmonella Crisis (2024). All simulation data is pre-computed. No OpenAI API key is required to explore this demo."
                state="info"
                dismissButton={false}
              />
            )}

            {baselineData && interventionRuns.length > 0 && (
              <PInlineNotification
                heading="Strategy Verdict"
                description={generateVerdict(baselineData, interventionRuns)}
                state="success"
                dismissButton={false}
              />
            )}

            {baselineData && interventionRuns.length > 0 && (
              <div className="grid grid-cols-4 gap-static-sm">
                {metricTabs.map((tab) => {
                  const bVal = (baselineData.metrics.at(-1)?.[tab.key] as number) ?? 0;
                  const bestInterv = interventionRuns.reduce((best, rd) => {
                    const val = (rd.metrics.at(-1)?.[tab.key] as number) ?? 0;
                    if (tab.higherIsBetter) return val > best ? val : best;
                    return val < best ? val : best;
                  }, tab.higherIsBetter ? -Infinity : Infinity);
                  return (
                    <ScoreCard
                      key={tab.key}
                      label={tab.label}
                      baseline={bVal}
                      best={bestInterv}
                      icon={tab.icon}
                      higherIsBetter={tab.higherIsBetter}
                    />
                  );
                })}
              </div>
            )}

            <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md">
              <div className="flex items-center justify-between mb-fluid-sm flex-wrap gap-static-sm">
                <PHeading size="small">Trajectory Comparison</PHeading>
                <div className="flex gap-static-xs flex-wrap">
                  {metricTabs.map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => setActiveMetric(tab.key)}
                      className={`flex items-center gap-static-xs px-static-sm py-static-xs rounded border text-xs transition-colors ${
                        activeMetric === tab.key
                          ? "border-primary bg-primary text-[white]"
                          : "border-contrast-low bg-canvas text-contrast-medium hover:border-primary hover:text-primary"
                      }`}
                      style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
                    >
                      <PIcon name={tab.icon} size="small" color="inherit" />
                      <span style={{ color: "inherit" }}>{tab.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="mb-fluid-sm flex flex-wrap gap-static-sm">
                {allRuns.map((rd) => (
                  <div key={rd.run.id} className="flex items-center gap-static-xs">
                    <div className="w-3 h-0.5" style={{ backgroundColor: getRunColor(rd.run) }} />
                    <PText size="small" className="text-contrast-medium">{getRunLabel(rd.run)}</PText>
                  </div>
                ))}
              </div>

              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#D8D8DB" />
                  <XAxis
                    dataKey="round"
                    label={{ value: "Round", position: "insideBottomRight", offset: -10, style: { fontSize: 11 } }}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis domain={activeMetric === "sentiment_score" ? [-1, 1] : [0, 1]} tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: "#EEEFF2",
                      border: "1px solid #D8D8DB",
                      borderRadius: "4px",
                      fontSize: 12,
                    }}
                    formatter={(value: unknown, name: unknown) => {
                      const nameStr = String(name);
                      const rd = allRuns.find((r) => r.run.id === nameStr);
                      return [typeof value === "number" ? value.toFixed(3) : String(value), rd ? getRunLabel(rd.run) : nameStr] as [string, string];
                    }}
                  />
                  {activeMetric === "sentiment_score" && (
                    <ReferenceLine y={0} stroke="#6B6D70" strokeDasharray="4 4" />
                  )}
                  {allRuns.map((rd) => (
                    <Line
                      key={rd.run.id}
                      type="monotone"
                      dataKey={rd.run.id}
                      stroke={getRunColor(rd.run)}
                      strokeWidth={rd.run.run_type === "baseline" ? 2 : 2.5}
                      strokeDasharray={rd.run.run_type === "baseline" ? "6 3" : undefined}
                      dot={{ r: 4, fill: getRunColor(rd.run) }}
                      activeDot={{ r: 6 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>

              <PText size="small" className="text-contrast-low text-center mt-static-xs">
                {activeTabCfg.higherIsBetter ? "Higher is better" : "Lower is better"} —
                Baseline shown as dashed line
              </PText>
            </div>

            <div className="bg-surface border border-contrast-low rounded-lg overflow-hidden">
              <div className="px-fluid-md py-static-md border-b border-contrast-low">
                <PHeading size="small">Agent-Level Response Breakdown</PHeading>
              </div>
              <div className="divide-y divide-contrast-low">
                {allRuns.map((rd) => (
                  <div key={rd.run.id} className="p-fluid-sm">
                    <div className="flex items-center gap-static-sm mb-static-sm">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getRunColor(rd.run) }} />
                      <PText size="small" weight="semi-bold">{getRunLabel(rd.run)}</PText>
                      <PTag color={rd.run.run_type === "baseline" ? "background-frosted" : "notification-warning-soft"}>
                        {rd.run.run_type}
                      </PTag>
                    </div>

                    <div className="flex flex-col gap-static-xs">
                      {rd.rounds.map((state) => (
                        <div key={state.id}>
                          <button
                            onClick={() => setExpandedRound(expandedRound === state.id ? null : state.id)}
                            className="w-full flex items-center justify-between px-static-sm py-static-xs rounded hover:bg-canvas transition-colors text-left"
                            style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
                          >
                            <div className="flex items-center gap-static-sm">
                              <PText size="small" weight="semi-bold">Round {state.round_number}</PText>
                              {state.strategy_applied && (
                                <PTag color="notification-warning-soft">
                                  {STRATEGY_LABELS[state.strategy_applied as StrategyType]} applied
                                </PTag>
                              )}
                            </div>
                            <div className="flex items-center gap-static-md">
                              <PText size="small" className="text-contrast-medium">
                                Sentiment: <span className={state.overall_sentiment > 0 ? "text-success" : "text-error"}>
                                  {state.overall_sentiment.toFixed(2)}
                                </span>
                              </PText>
                              <PText size="small" className="text-contrast-medium">
                                Polarization: {state.polarization_level.toFixed(2)}
                              </PText>
                              <PIcon name={expandedRound === state.id ? "arrow-head-up" : "arrow-head-down"} size="small" color="contrast-medium" />
                            </div>
                          </button>

                          {expandedRound === state.id && (
                            <div className="mt-static-xs mx-static-sm bg-canvas border border-contrast-low rounded p-static-sm flex flex-col gap-static-sm">
                              <PText size="small" className="text-contrast-medium italic mb-static-xs">
                                {state.narrative_state}
                              </PText>
                              {state.agent_responses.map((resp: AgentResponse, i: number) => {
                                const roleKey = resp.role as keyof typeof AGENT_ROLE_COLORS;
                                const colors = AGENT_ROLE_COLORS[roleKey] || AGENT_ROLE_COLORS.consumer;
                                return (
                                  <div key={i} className="flex gap-static-sm">
                                    <div className={`w-5 h-5 shrink-0 rounded-full flex items-center justify-center mt-0.5 ${colors.bg}`}>
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
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
