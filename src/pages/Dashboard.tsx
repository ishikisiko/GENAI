import type { ComponentProps } from "react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  PHeading, PText, PButton, PButtonPure, PIcon, PSpinner, PDivider, PInlineNotification, PTag,
} from "@porsche-design-system/components-react";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { getErrorMessage } from "../lib/errors";
import { supabase } from "../lib/supabase";
import { seedDemo, isDemoAlreadySeeded, DEMO_CASE_ID } from "../lib/seedDemo";
import type { CrisisCase } from "../lib/types";
import { useI18n } from "../lib/i18n";

type IconName = NonNullable<ComponentProps<typeof PIcon>["name"]>;

export default function Dashboard() {
  const { t } = useI18n();
  const [cases, setCases] = useState<CrisisCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);
  const [demoExists, setDemoExists] = useState(false);
  const navigate = useNavigate();

  const fetchCases = useCallback(async () => {
    const [{ data }, alreadySeeded] = await Promise.all([
      supabase.from("crisis_cases").select("*").order("created_at", { ascending: false }),
      isDemoAlreadySeeded(),
    ]);
    return { cases: data ?? [], alreadySeeded };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function runInitialLoad() {
      const { cases, alreadySeeded } = await fetchCases();
      if (cancelled) return;
      setCases(cases);
      setDemoExists(alreadySeeded);
      setLoading(false);
    }

    void runInitialLoad();

    return () => {
      cancelled = true;
    };
  }, [fetchCases]);

  async function handleLoadDemo() {
    setDemoLoading(true);
    setDemoError(null);
    try {
      await seedDemo();
      navigate(`/cases/${DEMO_CASE_ID}/comparison`);
    } catch (error: unknown) {
      setDemoError(getErrorMessage(error, "Failed to load demo. Please try again."));
      setDemoLoading(false);
    }
  }

  const getNextStep = (c: CrisisCase) => {
    if (c.status === "draft") return `/cases/${c.id}/documents`;
    if (c.status === "grounded") return `/cases/${c.id}/grounding`;
    if (c.status === "agents_ready") return `/cases/${c.id}/simulation`;
    return `/cases/${c.id}/comparison`;
  };

  const getNextStepLabel = (c: CrisisCase) => {
    if (c.status === "draft") return t("documents.addToCase");
    if (c.status === "grounded") return t("nav.grounding");
    if (c.status === "agents_ready") return t("simulation.runBaseline");
    return t("dashboard.viewDemo");
  };

  const dashboardStats = [
    { label: t("dashboard.totalCases"), value: cases.length, icon: "document" },
    { label: t("dashboard.simulated"), value: cases.filter((c) => c.status === "simulated").length, icon: "chart" },
    { label: t("dashboard.inProgress"), value: cases.filter((c) => c.status !== "simulated").length, icon: "clock" },
  ] satisfies { label: string; value: number; icon: IconName }[];

  return (
    <div className="min-h-full">
      <PageHeader
        title={t("dashboard.title")}
        subtitle={t("dashboard.subtitle")}
        action={
          <div className="flex items-center gap-static-sm">
            {demoExists ? (
              <PButtonPure
                icon="ai-spark"
                onClick={() => navigate(`/cases/${DEMO_CASE_ID}/comparison`)}
              >
                {t("dashboard.viewDemo")}
              </PButtonPure>
            ) : (
              <PButtonPure
                icon="ai-spark"
                onClick={handleLoadDemo}
                loading={demoLoading}
              >
                {t("dashboard.loadDemo")}
              </PButtonPure>
            )}
            <PButton icon="add" onClick={() => navigate("/cases/new")}>
              {t("dashboard.newCase")}
            </PButton>
          </div>
        }
      />

      <div className="p-fluid-lg">
        {demoError && (
          <div className="mb-fluid-sm w-full">
            <PInlineNotification
              heading="Demo load failed"
              description={demoError}
              state="error"
              dismissButton
              onDismiss={() => setDemoError(null)}
            />
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-fluid-xxl">
            <PSpinner size="medium" />
          </div>
        ) : cases.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-fluid-xxl gap-fluid-md text-center">
            <div className="w-20 h-20 rounded-full bg-surface flex items-center justify-center">
              <PIcon name="chart" size="large" color="contrast-medium" />
            </div>
            <div>
              <PHeading size="medium" className="mb-static-xs">{t("dashboard.noCases")}</PHeading>
              <PText className="text-contrast-medium max-w-sm">
                {t("dashboard.noCasesDesc")}
              </PText>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-static-sm">
              <PButton icon="add" onClick={() => navigate("/cases/new")}>
                {t("dashboard.createFirst")}
              </PButton>
              <PButton
                variant="secondary"
                icon="ai-spark"
                onClick={handleLoadDemo}
                loading={demoLoading}
              >
                {demoLoading ? `${t("dashboard.loadDemo")}...` : t("dashboard.loadDemoSimulation")}
              </PButton>
            </div>

            <div className="mt-fluid-sm w-full max-w-2xl bg-surface border border-contrast-low rounded-lg p-fluid-sm text-left">
              <div className="flex gap-static-sm">
                <PIcon name="information" color="contrast-medium" />
                <div>
                  <PText size="small" weight="semi-bold" className="mb-static-xs">{t("dashboard.demoInfoTitle")}</PText>
                  <PText size="small" className="text-contrast-medium">
                    {t("dashboard.demoInfoDesc")}
                  </PText>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-fluid-sm w-full">
            <div className="grid grid-cols-1 gap-fluid-md mb-fluid-md md:grid-cols-3">
              {dashboardStats.map((stat) => (
                <div key={stat.label} className="bg-surface border border-contrast-low rounded-lg p-fluid-sm flex items-center gap-static-md">
                  <div className="w-10 h-10 bg-canvas rounded-md flex items-center justify-center">
                    <PIcon name={stat.icon} color="contrast-medium" />
                  </div>
                  <div>
                    <PText size="small" className="text-contrast-medium">{stat.label}</PText>
                    <PHeading size="medium">{stat.value}</PHeading>
                  </div>
                </div>
              ))}
            </div>

            <PDivider className="mb-fluid-sm" />

            <div className="flex flex-col gap-static-md">
              {cases.map((c) => (
                <div
                  key={c.id}
                  className="bg-surface border border-contrast-low rounded-lg p-fluid-md hover:border-contrast-medium transition-colors cursor-pointer group"
                  onClick={() => navigate(getNextStep(c))}
                >
                  <div className="flex flex-col gap-static-md sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-static-sm mb-static-xs">
                        <StatusBadge status={c.status} />
                        {c.id === DEMO_CASE_ID && (
                          <PTag color="background-frosted" icon="ai-spark">Demo</PTag>
                        )}
                        <PText size="small" className="text-contrast-low">
                          {new Date(c.created_at).toLocaleDateString()}
                        </PText>
                      </div>
                      <PHeading size="small" className="mb-static-xs group-hover:text-primary transition-colors">
                        {c.title}
                      </PHeading>
                      <PText size="small" className="text-contrast-medium line-clamp-2">
                        {c.description || "No description provided."}
                      </PText>
                    </div>
                    <div className="shrink-0">
                      <PButton
                        variant="secondary"
                        onClick={(e) => { e.stopPropagation(); navigate(getNextStep(c)); }}
                      >
                        {getNextStepLabel(c)}
                      </PButton>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
