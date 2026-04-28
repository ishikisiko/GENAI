import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  PButton, PText, PHeading, PInlineNotification,
} from "@porsche-design-system/components-react";
import { supabase } from "../lib/supabase";
import PageHeader from "../components/PageHeader";
import { useI18n } from "../lib/i18n";

export default function CaseCreation() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleCreate() {
    if (!title.trim()) {
      setError("Please provide a case title.");
      return;
    }
    setLoading(true);
    setError("");
    const { data, error: err } = await supabase
      .from("crisis_cases")
      .insert({ title: title.trim(), description: description.trim(), status: "draft" })
      .select()
      .maybeSingle();

    if (err || !data) {
      setError(err?.message || "Failed to create case.");
      setLoading(false);
      return;
    }
    navigate(`/cases/${data.id}/documents`);
  }

  return (
    <div className="min-h-full">
      <PageHeader
        title={t("case.new.title")}
        subtitle={t("case.new.subtitle")}
        breadcrumbs={[{ label: t("common.dashboard"), href: "/" }, { label: t("nav.newCase") }]}
      />

      <div className="p-fluid-lg w-full">
        {error && (
          <PInlineNotification
            heading="Validation Error"
            description={error}
            state="error"
            dismissButton={false}
            className="mb-fluid-md"
          />
        )}

        <div className="bg-surface border border-contrast-low rounded-lg p-fluid-md flex flex-col gap-fluid-sm">
          <div>
            <PHeading size="small" className="mb-fluid-sm">{t("case.new.details")}</PHeading>
            <PText size="small" className="text-contrast-medium mb-fluid-md">
              {t("case.new.detailsDesc")}
            </PText>
          </div>

          <div className="flex flex-col gap-static-xs">
            <label className="text-static-sm font-semibold text-primary">
              <PText size="small" weight="semi-bold">{t("case.new.titleLabel")}</PText>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("case.new.titlePlaceholder")}
              className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary placeholder:text-contrast-low focus:outline-none focus:border-primary transition-colors"
              style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "16px" }}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            />
          </div>

          <div className="flex flex-col gap-static-xs">
            <PText size="small" weight="semi-bold">{t("case.new.description")}</PText>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("case.new.descriptionPlaceholder")}
              rows={4}
              className="w-full border border-contrast-low rounded bg-canvas px-static-md py-static-sm text-primary placeholder:text-contrast-low focus:outline-none focus:border-primary transition-colors resize-none"
              style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif", fontSize: "16px" }}
            />
          </div>

          <div className="pt-fluid-sm border-t border-contrast-low flex flex-wrap gap-static-md">
            <PButton
              loading={loading}
              disabled={loading || !title.trim()}
              icon="arrow-right"
              onClick={handleCreate}
            >
              {t("case.new.create")}
            </PButton>
            <PButton variant="secondary" onClick={() => navigate("/")}>
              {t("common.cancel")}
            </PButton>
          </div>
        </div>

        <div className="mt-fluid-md bg-notification-info-soft border border-notification-info rounded-lg p-fluid-sm">
          <div className="flex gap-static-sm">
            <PText size="small" weight="semi-bold" className="text-info">{t("case.new.nextTitle")}</PText>
          </div>
          <PText size="small" className="text-contrast-high mt-static-xs">
            {t("case.new.nextDesc")}
          </PText>
        </div>
      </div>
    </div>
  );
}
