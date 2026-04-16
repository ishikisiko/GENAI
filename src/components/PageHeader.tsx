import { useNavigate } from "react-router-dom";
import { PHeading, PText, PButtonPure } from "@porsche-design-system/components-react";
import type { ReactNode } from "react";

interface Breadcrumb {
  label: string;
  href?: string;
}

interface Props {
  title: string;
  subtitle?: string;
  breadcrumbs?: Breadcrumb[];
  action?: ReactNode;
}

export default function PageHeader({ title, subtitle, breadcrumbs, action }: Props) {
  const navigate = useNavigate();

  return (
    <div className="border-b border-contrast-low bg-canvas px-fluid-lg py-fluid-md">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <div className="flex items-center gap-static-xs mb-static-sm">
          {breadcrumbs.map((b, i) => (
            <div key={i} className="flex items-center gap-static-xs">
              {i > 0 && <PText size="x-small" className="text-contrast-low">/</PText>}
              {b.href ? (
                <PButtonPure
                  size="x-small"
                  onClick={() => navigate(b.href!)}
                  className="text-contrast-medium hover:text-primary"
                >
                  {b.label}
                </PButtonPure>
              ) : (
                <PText size="x-small" className="text-contrast-medium">{b.label}</PText>
              )}
            </div>
          ))}
        </div>
      )}
      <div className="flex items-start justify-between gap-static-md">
        <div>
          <PHeading size="large" tag="h1">{title}</PHeading>
          {subtitle && (
            <PText className="text-contrast-medium mt-static-xs">{subtitle}</PText>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </div>
  );
}
