import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BarChart3,
  Languages,
  Sparkles,
  ShieldCheck,
  Users,
  Megaphone,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { BrandMark } from "@/components/common/brand-mark";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Multilingua — AI Multilingual Communication Platform" },
      {
        name: "description",
        content:
          "The enterprise platform for governments, NGOs, and organizations to run AI-personalized multilingual campaigns at scale.",
      },
    ],
  }),
  component: LandingPage,
});

const features = [
  {
    icon: Sparkles,
    title: "AI content generation",
    description:
      "Draft on-brand campaign copy in any language with governance-ready review workflows.",
  },
  {
    icon: Languages,
    title: "120+ languages",
    description:
      "Localize once, deliver everywhere with dialect-aware translation and cultural adaptation.",
  },
  {
    icon: Users,
    title: "Audience segmentation",
    description:
      "Personalize reach by geography, language, demographics, and engagement history.",
  },
  {
    icon: Megaphone,
    title: "Omnichannel delivery",
    description: "SMS, email, WhatsApp, IVR, and social — orchestrated from one console.",
  },
  {
    icon: BarChart3,
    title: "Real-time analytics",
    description:
      "Track reach, comprehension, and outcomes with dashboards built for public accountability.",
  },
  {
    icon: ShieldCheck,
    title: "Enterprise security",
    description:
      "Role-based access, audit trails, and SOC 2-ready controls for regulated organizations.",
  },
];

function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link to="/">
            <BrandMark />
          </Link>
          <nav className="hidden items-center gap-6 text-sm font-medium text-muted-foreground md:flex">
            <a href="#features" className="hover:text-foreground">Features</a>
            <a href="#audience" className="hover:text-foreground">Who it's for</a>
            <a href="#security" className="hover:text-foreground">Security</a>
          </nav>
          <div className="flex items-center gap-2">
            <Button variant="ghost" asChild>
              <Link to="/login">Sign in</Link>
            </Button>
            <Button asChild>
              <Link to="/register">
                Get started <ArrowRight className="ml-1.5 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,var(--color-primary)/10,transparent_60%)]" />
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mx-auto max-w-3xl text-center"
          >
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
              <Sparkles className="h-3 w-3 text-accent" />
              AI-powered multilingual outreach
            </span>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
              Communicate with every citizen, in every language.
            </h1>
            <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
              The enterprise platform for governments, NGOs, healthcare, and education to
              plan, personalize, and deliver public awareness campaigns at national scale.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Button size="lg" asChild>
                <Link to="/register">
                  Start free trial <ArrowRight className="ml-1.5 h-4 w-4" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link to="/dashboard">View dashboard</Link>
              </Button>
            </div>

            <div className="mt-10 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-xs text-muted-foreground">
              {["Trusted by public sector", "SOC 2 ready", "99.99% delivery uptime"].map(
                (item) => (
                  <div key={item} className="flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5 text-accent" />
                    <span>{item}</span>
                  </div>
                ),
              )}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="border-t border-border bg-card/50 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-sm font-semibold uppercase tracking-wider text-primary">
              Platform
            </p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
              Everything you need for large-scale outreach
            </h2>
            <p className="mt-3 text-muted-foreground">
              An integrated suite for content, audience, delivery, and measurement.
            </p>
          </div>
          <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.4, delay: i * 0.05 }}
                className="rounded-2xl border border-border bg-card p-6 shadow-card"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <f.icon className="h-5 w-5" />
                </div>
                <h3 className="mt-4 text-base font-semibold text-foreground">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {f.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section id="security" className="py-20">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="overflow-hidden rounded-3xl bg-secondary p-10 text-secondary-foreground shadow-elevated sm:p-14">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-semibold tracking-tight">
                Ready to modernize your public communications?
              </h2>
              <p className="mt-3 text-secondary-foreground/70">
                Book a walkthrough with our team, or start with a self-serve trial.
              </p>
              <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                <Button size="lg" asChild>
                  <Link to="/register">Create account</Link>
                </Button>
                <Button size="lg" variant="outline" className="border-secondary-foreground/20 bg-transparent text-secondary-foreground hover:bg-secondary-foreground/10 hover:text-secondary-foreground" asChild>
                  <Link to="/login">Sign in</Link>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-border bg-card py-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 text-xs text-muted-foreground sm:flex-row sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <BrandMark compact />
            <span>&copy; {new Date().getFullYear()} Multilingua. All rights reserved.</span>
          </div>
          <div className="flex items-center gap-4">
            <a href="#" className="hover:text-foreground">Privacy</a>
            <a href="#" className="hover:text-foreground">Terms</a>
            <a href="#" className="hover:text-foreground">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
