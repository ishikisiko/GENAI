import type { ComponentProps, ReactNode } from "react";
import { PIcon, PDivider, PText } from "@porsche-design-system/components-react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useI18n } from "../lib/i18n";

type IconName = NonNullable<ComponentProps<typeof PIcon>["name"]>;

interface NavItem {
  label: string;
  icon: IconName;
  href: string;
  exact?: boolean;
}

function CaseNav({ caseId }: { caseId: string }) {
  const { t } = useI18n();
  const items: NavItem[] = [
    { label: t("nav.documents"), icon: "document", href: `/cases/${caseId}/documents` },
    { label: t("nav.discovery"), icon: "search", href: `/cases/${caseId}/source-discovery` },
    { label: t("nav.grounding"), icon: "brain", href: `/cases/${caseId}/grounding` },
    { label: t("nav.simulation"), icon: "chart", href: `/cases/${caseId}/simulation` },
    { label: t("nav.comparison"), icon: "compare", href: `/cases/${caseId}/comparison` },
  ];
  const location = useLocation();

  return (
    <div className="mt-fluid-md">
      <PText size="small" className="text-contrast-medium uppercase tracking-widest px-static-sm mb-static-xs" style={{ fontSize: "10px" }}>
        {t("nav.caseSteps")}
      </PText>
      <div className="flex flex-wrap gap-static-xs mt-static-xs lg:flex-col">
        {items.map((item) => {
          const active = location.pathname === item.href || (
            item.href.endsWith("/source-discovery") && (
              location.pathname.includes("/source-discovery")
              || location.pathname.includes("/evidence-packs")
            )
          );
          return (
            <Link
              key={item.href}
              to={item.href}
              className={`flex items-center gap-static-sm px-static-sm py-static-xs rounded transition-colors ${
                active
                  ? "bg-surface text-primary"
                  : "text-contrast-medium hover:text-primary hover:bg-surface"
              }`}
            >
              <PIcon name={item.icon} size="small" />
              <PText size="small" weight={active ? "semi-bold" : "regular"} style={{ color: "inherit" }}>
                {item.label}
              </PText>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function LanguageToggle() {
  const { language, setLanguage, t } = useI18n();

  return (
    <div className="flex rounded border border-contrast-low overflow-hidden" aria-label="Language">
      {(["zh", "en"] as const).map((nextLanguage) => {
        const active = language === nextLanguage;
        return (
          <button
            key={nextLanguage}
            type="button"
            onClick={() => setLanguage(nextLanguage)}
            className={`px-static-sm py-static-xs text-xs font-semibold transition-colors ${
              active
                ? "bg-primary text-[white]"
                : "bg-canvas text-contrast-medium hover:text-primary"
            }`}
            style={{ fontFamily: "'Porsche Next','Arial Narrow',Arial,sans-serif" }}
          >
            {t(nextLanguage === "zh" ? "lang.zh" : "lang.en")}
          </button>
        );
      })}
    </div>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const { caseId } = useParams<{ caseId: string }>();
  const { t } = useI18n();

  const globalNav: NavItem[] = [
    { label: t("nav.dashboard"), icon: "home", href: "/", exact: true },
    { label: t("nav.sourceLibrary"), icon: "document", href: "/sources" },
    { label: t("nav.newCase"), icon: "add", href: "/cases/new" },
  ];

  return (
    <div className="min-h-screen bg-canvas flex flex-col lg:flex-row">
      <aside className="w-full shrink-0 border-b border-contrast-low bg-surface flex flex-col lg:w-56 lg:border-b-0 lg:border-r">
        <div className="p-fluid-sm border-b border-contrast-low">
          <div className="flex items-center justify-between gap-static-sm">
            <div className="flex items-center gap-static-sm">
            <div className="w-8 h-8 bg-primary rounded flex items-center justify-center" style={{ color: "white" }}>
              <PIcon name="chart" size="small" color="inherit" />
            </div>
            <div>
              <PText size="small" weight="semi-bold" className="text-primary leading-tight">
                {t("app.name")}
              </PText>
              <PText size="small" className="text-contrast-medium leading-tight" style={{ fontSize: "11px" }}>
                {t("app.subtitle")}
              </PText>
            </div>
            </div>
            <div className="lg:hidden">
              <LanguageToggle />
            </div>
          </div>
        </div>

        <nav className="flex-1 p-fluid-sm">
          <div className="flex flex-wrap gap-static-xs lg:flex-col">
            {globalNav.map((item) => {
              const active = item.exact
                ? location.pathname === item.href
                : location.pathname.startsWith(item.href) && item.href !== "/";
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={`flex items-center gap-static-sm px-static-sm py-static-xs rounded transition-colors ${
                    active
                      ? "bg-primary text-[white]"
                      : "text-contrast-medium hover:text-primary hover:bg-surface"
                  }`}
                >
                  <PIcon name={item.icon} size="small" color="inherit" className={active ? "invert" : undefined} />
                  <span className="text-sm font-medium" style={{ color: "inherit" }}>
                    {item.label}
                  </span>
                </Link>
              );
            })}
          </div>

          {caseId && (
            <>
              <PDivider className="my-fluid-sm" />
              <CaseNav caseId={caseId} />
            </>
          )}
        </nav>

        <div className="hidden p-fluid-sm border-t border-contrast-low lg:flex lg:flex-col lg:items-center lg:gap-static-sm">
          <LanguageToggle />
          <PText size="small" className="text-contrast-low text-center" style={{ fontSize: "11px" }}>
            {t("app.version")}
          </PText>
        </div>
      </aside>

      <main className="flex-1 min-w-0 overflow-auto">
        {children}
      </main>
    </div>
  );
}
