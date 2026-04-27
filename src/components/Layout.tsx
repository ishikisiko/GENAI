import type { ComponentProps, ReactNode } from "react";
import { PIcon, PDivider, PText } from "@porsche-design-system/components-react";
import { Link, useLocation, useParams } from "react-router-dom";

type IconName = NonNullable<ComponentProps<typeof PIcon>["name"]>;

interface NavItem {
  label: string;
  icon: IconName;
  href: string;
  exact?: boolean;
}

const globalNav: NavItem[] = [
  { label: "Dashboard", icon: "home", href: "/", exact: true },
  { label: "Source Library", icon: "document", href: "/sources" },
  { label: "New Case", icon: "add", href: "/cases/new" },
];

function CaseNav({ caseId }: { caseId: string }) {
  const items: NavItem[] = [
    { label: "Documents", icon: "document", href: `/cases/${caseId}/documents` },
    { label: "Discovery", icon: "search", href: `/cases/${caseId}/source-discovery` },
    { label: "Grounding", icon: "brain", href: `/cases/${caseId}/grounding` },
    { label: "Simulation", icon: "chart", href: `/cases/${caseId}/simulation` },
    { label: "Comparison", icon: "compare", href: `/cases/${caseId}/comparison` },
  ];
  const location = useLocation();

  return (
    <div className="mt-fluid-md">
      <PText size="small" className="text-contrast-medium uppercase tracking-widest px-static-sm mb-static-xs" style={{ fontSize: "10px" }}>
        Case Steps
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
              <PText size="small" weight={active ? "semi-bold" : "regular"}>
                {item.label}
              </PText>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const { caseId } = useParams<{ caseId: string }>();

  return (
    <div className="min-h-screen bg-canvas flex flex-col lg:flex-row">
      <aside className="w-full shrink-0 border-b border-contrast-low bg-surface flex flex-col lg:w-56 lg:border-b-0 lg:border-r">
        <div className="p-fluid-sm border-b border-contrast-low">
          <div className="flex items-center gap-static-sm">
            <div className="w-8 h-8 bg-primary rounded flex items-center justify-center" style={{ color: "white" }}>
              <PIcon name="chart" size="small" color="inherit" />
            </div>
            <div>
              <PText size="small" weight="semi-bold" className="text-primary leading-tight">
                CrisisSim
              </PText>
              <PText size="small" className="text-contrast-medium leading-tight" style={{ fontSize: "11px" }}>
                Response Simulator
              </PText>
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
                  <PIcon name={item.icon} size="small" color="inherit" />
                  <PText size="small" weight={active ? "semi-bold" : "regular"} style={{ color: "inherit" }}>
                    {item.label}
                  </PText>
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

        <div className="hidden p-fluid-sm border-t border-contrast-low lg:block">
          <PText size="small" className="text-contrast-low text-center" style={{ fontSize: "11px" }}>
            MVP v1.0
          </PText>
        </div>
      </aside>

      <main className="flex-1 min-w-0 overflow-auto">
        {children}
      </main>
    </div>
  );
}
