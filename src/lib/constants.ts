import type { AgentRole, DocType, StrategyType } from "./types";

export const DOC_TYPE_LABELS: Record<DocType, string> = {
  news: "News Report",
  complaint: "User Complaint",
  statement: "Official Statement",
};

export const DOC_TYPE_COLORS: Record<DocType, string> = {
  news: "notification-info",
  complaint: "notification-warning",
  statement: "notification-success",
};

export const AGENT_ROLE_LABELS: Record<AgentRole, string> = {
  consumer: "Consumer",
  supporter: "Supporter",
  critic: "Critic",
  media: "Media",
};

export const AGENT_ROLE_COLORS: Record<AgentRole, { bg: string; text: string }> = {
  consumer: { bg: "bg-info-soft", text: "text-info" },
  supporter: { bg: "bg-success-soft", text: "text-success" },
  critic: { bg: "bg-error-soft", text: "text-error" },
  media: { bg: "bg-warning-soft", text: "text-warning" },
};

export const STRATEGY_LABELS: Record<StrategyType, string> = {
  apology: "Apology",
  clarification: "Clarification",
  compensation: "Compensation",
  rebuttal: "Rebuttal",
};

export const STRATEGY_DESCRIPTIONS: Record<StrategyType, string> = {
  apology: "Acknowledge responsibility and express sincere remorse",
  clarification: "Provide accurate facts to correct misunderstandings",
  compensation: "Offer tangible remedies to affected parties",
  rebuttal: "Challenge inaccurate claims with counter-evidence",
};

export const STRATEGY_ICONS: Record<StrategyType, string> = {
  apology: "heart",
  clarification: "information",
  compensation: "gift",
  rebuttal: "exclamation",
};

export const CASE_STATUS_STEPS = [
  { key: "draft", label: "Draft" },
  { key: "grounded", label: "Grounded" },
  { key: "agents_ready", label: "Agents Ready" },
  { key: "simulated", label: "Simulated" },
] as const;

export const STATUS_STEP_INDEX: Record<string, number> = {
  draft: 0,
  grounded: 1,
  agents_ready: 2,
  simulated: 3,
};
