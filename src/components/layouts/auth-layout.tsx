import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { BrandMark } from "@/components/common/brand-mark";

interface AuthLayoutProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <div className="grid min-h-screen w-full lg:grid-cols-2">
      <div className="flex flex-col justify-between px-6 py-8 sm:px-10">
        <Link to="/" className="inline-flex">
          <BrandMark />
        </Link>

        <div className="mx-auto w-full max-w-md py-12">
          <div className="mb-8">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
            {subtitle && (
              <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>
          {children}
          {footer && <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>}
        </div>

        <p className="text-xs text-muted-foreground">
          &copy; {new Date().getFullYear()} All rights reserved.
        </p>
      </div>

      <div className="relative hidden overflow-hidden bg-secondary lg:block">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,var(--color-primary)/25,transparent_55%),radial-gradient(circle_at_bottom_left,var(--color-accent)/20,transparent_60%)]" />
        <div className="relative flex h-full flex-col justify-between p-12 text-secondary-foreground">
          <div className="max-w-md">
            <p className="text-xs font-semibold uppercase tracking-widest text-accent">
              Enterprise Platform
            </p>
            <h2 className="mt-4 text-3xl font-semibold leading-tight">
              Reach every audience, in every language, with AI-crafted precision.
            </h2>
            <p className="mt-4 text-sm text-secondary-foreground/70">
              Plan, personalize, and deliver multilingual campaigns at scale — with the
              governance and analytics enterprise teams require.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-4 text-xs text-secondary-foreground/70">
            <div>
              <p className="text-2xl font-semibold text-secondary-foreground">120+</p>
              <p>Languages supported</p>
            </div>
            <div>
              <p className="text-2xl font-semibold text-secondary-foreground">99.99%</p>
              <p>Delivery uptime</p>
            </div>
            <div>
              <p className="text-2xl font-semibold text-secondary-foreground">SOC 2</p>
              <p>Compliance ready</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
