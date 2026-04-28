import type { ComponentProps } from "react";
import { PTag } from "@porsche-design-system/components-react";
import type { CaseStatus } from "../lib/types";
import { useI18n, type CopyKey } from "../lib/i18n";

type TagColor = NonNullable<ComponentProps<typeof PTag>["color"]>;

const STATUS_CONFIG: Record<CaseStatus, { color: TagColor; labelKey: CopyKey }> = {
  draft: { color: "background-frosted", labelKey: "status.draft" },
  grounded: { color: "notification-info-soft", labelKey: "status.grounded" },
  agents_ready: { color: "notification-warning-soft", labelKey: "status.agents_ready" },
  simulated: { color: "notification-success-soft", labelKey: "status.simulated" },
};

export default function StatusBadge({ status }: { status: CaseStatus }) {
  const { t } = useI18n();
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
  return <PTag color={cfg.color}>{t(cfg.labelKey)}</PTag>;
}
