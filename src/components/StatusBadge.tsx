import type { ComponentProps } from "react";
import { PTag } from "@porsche-design-system/components-react";
import type { CaseStatus } from "../lib/types";

type TagColor = NonNullable<ComponentProps<typeof PTag>["color"]>;

const STATUS_CONFIG: Record<CaseStatus, { color: TagColor; label: string }> = {
  draft: { color: "background-frosted", label: "Draft" },
  grounded: { color: "notification-info-soft", label: "Grounded" },
  agents_ready: { color: "notification-warning-soft", label: "Agents Ready" },
  simulated: { color: "notification-success-soft", label: "Simulated" },
};

export default function StatusBadge({ status }: { status: CaseStatus }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
  return <PTag color={cfg.color}>{cfg.label}</PTag>;
}
