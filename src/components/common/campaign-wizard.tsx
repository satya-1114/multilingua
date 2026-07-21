import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, ChevronLeft, ChevronRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { audienceService } from "@/services/audience.service";
import { tagService, groupService } from "@/services/tag.service";
import { templateService } from "@/services/template.service";
import { organizationService } from "@/services/organization.service";
import type { CampaignInput, CampaignSchedule, Campaign } from "@/types/campaign";
import {
  CAMPAIGN_CATEGORIES,
  CAMPAIGN_COLORS,
  CAMPAIGN_PRIORITIES,
  CAMPAIGN_TYPES,
  CAMPAIGN_VISIBILITIES,
} from "@/constants/campaign";
import { LANGUAGES } from "@/constants/india";
import { cn } from "@/lib/utils";

const STEPS = ["Basics", "Audience", "Template", "Schedule", "Review"] as const;
type StepIdx = 0 | 1 | 2 | 3 | 4;

export interface CampaignWizardProps {
  initial?: Partial<CampaignInput> & { id?: string };
  submitLabel?: string;
  onSubmit: (input: CampaignInput) => Promise<Campaign | void> | Campaign | void;
  onCancel?: () => void;
}

const DEFAULT_INPUT: CampaignInput = {
  name: "",
  description: "",
  objective: "",
  type: "awareness",
  category: "government",
  priority: "medium",
  visibility: "organization",
  color: CAMPAIGN_COLORS[0]!,
  tags: [],
  organizationId: "",
  department: "",
  ownerId: "user-1",
  audienceGroupIds: [],
  audienceContactIds: [],
  languages: ["en"],
  schedule: { mode: "draft", timezone: "Asia/Kolkata" },
};

export function CampaignWizard({ initial, submitLabel = "Create campaign", onSubmit, onCancel }: CampaignWizardProps) {
  const [step, setStep] = useState<StepIdx>(0);
  const [state, setState] = useState<CampaignInput>({ ...DEFAULT_INPUT, ...initial });
  const [saving, setSaving] = useState(false);
  const [tagInput, setTagInput] = useState("");
  const codeRef = useRef<string>(
    `CMP-${new Date().getFullYear()}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`,
  );

  const orgQ = useQuery({ queryKey: ["orgs", "all"], queryFn: () => organizationService.listAll() });
  const tagsQ = useQuery({ queryKey: ["audience", "tags"], queryFn: () => tagService.list() });
  const groupsQ = useQuery({ queryKey: ["audience", "groups"], queryFn: () => groupService.list() });
  const audienceStatsQ = useQuery({ queryKey: ["audience", "stats"], queryFn: () => audienceService.getStats() });
  const templatesQ = useQuery({ queryKey: ["templates", "all"], queryFn: () => templateService.listAll({ status: ["published"] }) });

  useEffect(() => {
    if (!state.organizationId && orgQ.data?.length) {
      setState((s) => ({ ...s, organizationId: orgQ.data![0]!.id }));
    }
  }, [orgQ.data, state.organizationId]);

  const estimatedReach = useMemo(() => {
    return (groupsQ.data ?? [])
      .filter((g) => state.audienceGroupIds.includes(g.id))
      .reduce((acc, g) => acc + g.memberCount, 0);
  }, [groupsQ.data, state.audienceGroupIds]);

  const selectedTemplate = templatesQ.data?.find((t) => t.id === state.templateId);

  const errors = useMemo(() => {
    const errs: Partial<Record<keyof CampaignInput | `step${StepIdx}`, string>> = {};
    if (!state.name.trim()) errs.name = "Campaign name is required.";
    if (!state.organizationId) errs.organizationId = "Select an organization.";
    if (state.audienceGroupIds.length === 0) errs.audienceGroupIds = "Select at least one audience group.";
    if (state.languages.length === 0) errs.languages = "Select at least one language.";
    if (state.schedule.mode === "schedule" && !state.schedule.startAt) {
      errs.schedule = "Pick a start date and time.";
    }
    return errs;
  }, [state]);

  const canAdvance = (idx: StepIdx): boolean => {
    if (idx === 0) return !errors.name && !errors.organizationId;
    if (idx === 1) return !errors.audienceGroupIds;
    if (idx === 2) return true;
    if (idx === 3) return !errors.schedule;
    return true;
  };

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (Object.keys(errors).length > 0) return;
    setSaving(true);
    try {
      await onSubmit(state);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-6">
      <ol className="flex flex-wrap items-center gap-1 rounded-xl border bg-card p-2">
        {STEPS.map((label, i) => {
          const active = i === step;
          const done = i < step;
          return (
            <li key={label} className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setStep(i as StepIdx)}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors",
                  done && "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
                  active && "bg-primary text-primary-foreground shadow-sm",
                  !done && !active && "text-muted-foreground",
                )}
              >
                <span
                  className={cn(
                    "flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold ring-1",
                    done && "bg-emerald-500 text-white ring-emerald-500",
                    active && "bg-primary-foreground text-primary ring-primary-foreground",
                    !done && !active && "ring-border",
                  )}
                >
                  {done ? <Check className="h-3 w-3" /> : i + 1}
                </span>
                {label}
              </button>
              {i < STEPS.length - 1 && <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/60" />}
            </li>
          );
        })}
      </ol>

      {step === 0 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Basic information</CardTitle></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Field label="Campaign name" required error={errors.name}>
              <Input value={state.name} onChange={(e) => setState((s) => ({ ...s, name: e.target.value }))} placeholder="Monsoon Health Advisory 2026" />
            </Field>
            <Field label="Campaign code">
              <Input value={codeRef.current} readOnly disabled />
            </Field>
            <Field label="Type">
              <Select value={state.type} onValueChange={(v) => setState((s) => ({ ...s, type: v as CampaignInput["type"] }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CAMPAIGN_TYPES.map((t) => <SelectItem key={t.key} value={t.key}>{t.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Priority">
              <Select value={state.priority} onValueChange={(v) => setState((s) => ({ ...s, priority: v as CampaignInput["priority"] }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CAMPAIGN_PRIORITIES.map((p) => <SelectItem key={p.key} value={p.key}>{p.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Category">
              <Select value={state.category} onValueChange={(v) => setState((s) => ({ ...s, category: v as CampaignInput["category"] }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CAMPAIGN_CATEGORIES.map((c) => <SelectItem key={c.key} value={c.key}>{c.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Organization" required error={errors.organizationId}>
              <Select value={state.organizationId} onValueChange={(v) => setState((s) => ({ ...s, organizationId: v }))}>
                <SelectTrigger><SelectValue placeholder="Select organization" /></SelectTrigger>
                <SelectContent>
                  {(orgQ.data ?? []).map((o) => <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Department">
              <Input value={state.department ?? ""} onChange={(e) => setState((s) => ({ ...s, department: e.target.value }))} placeholder="Communications" />
            </Field>
            <Field label="Owner">
              <Input value={state.ownerId} onChange={(e) => setState((s) => ({ ...s, ownerId: e.target.value }))} />
            </Field>
            <Field label="Visibility" className="md:col-span-2">
              <RadioGroup
                value={state.visibility}
                onValueChange={(v) => setState((s) => ({ ...s, visibility: v as CampaignInput["visibility"] }))}
                className="grid gap-2 sm:grid-cols-3"
              >
                {CAMPAIGN_VISIBILITIES.map((v) => (
                  <label
                    key={v.key}
                    className={cn(
                      "flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm hover:border-primary",
                      state.visibility === v.key && "border-primary bg-primary/5",
                    )}
                  >
                    <RadioGroupItem value={v.key} className="mt-0.5" />
                    <div>
                      <p className="font-medium">{v.label}</p>
                      <p className="text-xs text-muted-foreground">{v.description}</p>
                    </div>
                  </label>
                ))}
              </RadioGroup>
            </Field>
            <Field label="Description" className="md:col-span-2">
              <Textarea rows={3} value={state.description ?? ""} onChange={(e) => setState((s) => ({ ...s, description: e.target.value }))} />
            </Field>
            <Field label="Objective" className="md:col-span-2">
              <Textarea rows={2} value={state.objective ?? ""} onChange={(e) => setState((s) => ({ ...s, objective: e.target.value }))} placeholder="What outcome does this campaign aim to achieve?" />
            </Field>
            <Field label="Campaign colour" className="md:col-span-2">
              <div className="flex flex-wrap gap-2">
                {CAMPAIGN_COLORS.map((c) => (
                  <button
                    type="button"
                    key={c}
                    onClick={() => setState((s) => ({ ...s, color: c }))}
                    className={cn(
                      "h-7 w-7 rounded-full ring-2 ring-transparent transition",
                      state.color === c && "ring-foreground",
                    )}
                    style={{ background: c }}
                    aria-label={`Colour ${c}`}
                  />
                ))}
              </div>
            </Field>
            <Field label="Tags" className="md:col-span-2">
              <div className="flex flex-wrap items-center gap-1.5">
                {state.tags.map((t) => (
                  <span key={t} className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs">
                    {t}
                    <button
                      type="button"
                      onClick={() => setState((s) => ({ ...s, tags: s.tags.filter((x) => x !== t) }))}
                      className="text-muted-foreground hover:text-foreground"
                      aria-label={`Remove ${t}`}
                    >×</button>
                  </span>
                ))}
                <Input
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && tagInput.trim()) {
                      e.preventDefault();
                      const v = tagInput.trim();
                      if (!state.tags.includes(v)) setState((s) => ({ ...s, tags: [...s.tags, v] }));
                      setTagInput("");
                    }
                  }}
                  placeholder="Add tag and press Enter"
                  className="h-8 w-48"
                />
              </div>
            </Field>
          </CardContent>
        </Card>
      )}

      {step === 1 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Audience selection</CardTitle></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div>
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">Audience groups</Label>
              <div className="mt-2 space-y-2">
                {(groupsQ.data ?? []).map((g) => {
                  const checked = state.audienceGroupIds.includes(g.id);
                  return (
                    <label
                      key={g.id}
                      className={cn(
                        "flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm hover:border-primary",
                        checked && "border-primary bg-primary/5",
                      )}
                    >
                      <Checkbox
                        checked={checked}
                        onCheckedChange={(v) =>
                          setState((s) => ({
                            ...s,
                            audienceGroupIds: v
                              ? [...s.audienceGroupIds, g.id]
                              : s.audienceGroupIds.filter((x) => x !== g.id),
                          }))
                        }
                      />
                      <div className="flex-1">
                        <p className="font-medium">{g.name}</p>
                        <p className="text-xs text-muted-foreground">{g.description}</p>
                      </div>
                      <span className="text-xs text-muted-foreground">{g.memberCount.toLocaleString()} members</span>
                    </label>
                  );
                })}
              </div>
              {errors.audienceGroupIds && (
                <p className="mt-2 text-xs text-destructive">{errors.audienceGroupIds}</p>
              )}
              <div className="mt-4">
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">Saved segment tags</Label>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {(tagsQ.data ?? []).map((t) => (
                    <span key={t.id} className="rounded-full bg-muted px-2 py-0.5 text-xs">
                      {t.name} <span className="text-muted-foreground">· {t.audienceCount}</span>
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <div className="space-y-3">
              <div className="rounded-lg border bg-muted/30 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Estimated reach</p>
                <p className="mt-1 text-2xl font-semibold">{estimatedReach.toLocaleString()}</p>
                <p className="text-xs text-muted-foreground">Across {state.audienceGroupIds.length} group(s)</p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Language distribution</p>
                <ul className="mt-2 space-y-1 text-sm">
                  {(audienceStatsQ.data?.languageDistribution ?? []).slice(0, 5).map((l) => (
                    <li key={l.language} className="flex items-center justify-between">
                      <span className="uppercase">{l.language}</span>
                      <span className="text-muted-foreground">{l.value}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-lg border bg-muted/30 p-4 text-xs text-muted-foreground">
                <p className="mb-1 font-semibold text-foreground">Duplicate detection</p>
                Contacts appearing in multiple selected groups are automatically de-duplicated during delivery.
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Communication template</CardTitle></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div>
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">Select existing template</Label>
              <div className="mt-2 max-h-72 space-y-2 overflow-y-auto pr-1">
                {(templatesQ.data ?? []).map((t) => {
                  const active = state.templateId === t.id;
                  return (
                    <button
                      type="button"
                      key={t.id}
                      onClick={() => setState((s) => ({ ...s, templateId: t.id }))}
                      className={cn(
                        "block w-full rounded-lg border p-3 text-left transition hover:border-primary",
                        active && "border-primary bg-primary/5",
                      )}
                    >
                      <p className="text-sm font-medium">{t.name}</p>
                      <p className="text-xs uppercase text-muted-foreground">{t.category} · {t.language}</p>
                      <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{t.body}</p>
                    </button>
                  );
                })}
              </div>
              <div className="mt-3">
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">Languages</Label>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {LANGUAGES.map((l) => {
                    const checked = state.languages.includes(l.code);
                    return (
                      <button
                        type="button"
                        key={l.code}
                        onClick={() =>
                          setState((s) => ({
                            ...s,
                            languages: checked ? s.languages.filter((x) => x !== l.code) : [...s.languages, l.code],
                          }))
                        }
                        className={cn(
                          "rounded-full border px-2 py-0.5 text-xs uppercase",
                          checked ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground",
                        )}
                      >
                        {l.code}
                      </button>
                    );
                  })}
                </div>
                {errors.languages && <p className="mt-2 text-xs text-destructive">{errors.languages}</p>}
              </div>
            </div>
            <div className="space-y-3">
              <div className="rounded-lg border bg-muted/30 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Preview</p>
                {selectedTemplate ? (
                  <>
                    {selectedTemplate.subject && (
                      <p className="mt-2 text-sm font-semibold">{selectedTemplate.subject}</p>
                    )}
                    <p className="mt-2 whitespace-pre-line text-sm text-foreground">{selectedTemplate.body}</p>
                    <div className="mt-3 flex flex-wrap gap-1 text-[11px] text-muted-foreground">
                      {selectedTemplate.variables.map((v) => (
                        <span key={v.key} className="rounded-full bg-primary/10 px-1.5 py-0.5 text-primary">
                          {`{{${v.key}}}`}
                        </span>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="mt-2 text-sm text-muted-foreground">Select a template to preview.</p>
                )}
              </div>
              <div className="rounded-lg border bg-muted/30 p-4 text-xs text-muted-foreground">
                <p className="mb-1 font-semibold text-foreground flex items-center gap-1">
                  <Sparkles className="h-3.5 w-3.5" /> Attachments
                </p>
                Media attachments and asset picker will appear here in the launch phase.
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 3 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Schedule</CardTitle></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Field label="Delivery mode" className="md:col-span-2">
              <RadioGroup
                value={state.schedule.mode}
                onValueChange={(v) => setState((s) => ({ ...s, schedule: { ...s.schedule, mode: v as CampaignSchedule["mode"] } }))}
                className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4"
              >
                {(["draft", "publish_now", "schedule", "recurring"] as CampaignSchedule["mode"][]).map((m) => (
                  <label
                    key={m}
                    className={cn(
                      "flex cursor-pointer items-start gap-2 rounded-lg border p-3 text-sm hover:border-primary",
                      state.schedule.mode === m && "border-primary bg-primary/5",
                    )}
                  >
                    <RadioGroupItem value={m} className="mt-0.5" />
                    <div>
                      <p className="font-medium capitalize">{m.replace("_", " ")}</p>
                      <p className="text-xs text-muted-foreground">
                        {m === "draft" && "Save without delivering."}
                        {m === "publish_now" && "Deliver immediately."}
                        {m === "schedule" && "Deliver at a specific time."}
                        {m === "recurring" && "Repeating cadence (coming soon)."}
                      </p>
                    </div>
                  </label>
                ))}
              </RadioGroup>
            </Field>
            <Field label="Timezone">
              <Input value={state.schedule.timezone} onChange={(e) => setState((s) => ({ ...s, schedule: { ...s.schedule, timezone: e.target.value } }))} />
            </Field>
            <Field label="Start date & time" error={errors.schedule}>
              <Input
                type="datetime-local"
                value={state.schedule.startAt?.slice(0, 16) ?? ""}
                onChange={(e) => setState((s) => ({ ...s, schedule: { ...s.schedule, startAt: e.target.value ? new Date(e.target.value).toISOString() : undefined } }))}
              />
            </Field>
            <Field label="End date & time">
              <Input
                type="datetime-local"
                value={state.schedule.endAt?.slice(0, 16) ?? ""}
                onChange={(e) => setState((s) => ({ ...s, schedule: { ...s.schedule, endAt: e.target.value ? new Date(e.target.value).toISOString() : undefined } }))}
              />
            </Field>
            <Field label="Expiry date">
              <Input
                type="datetime-local"
                value={state.schedule.expiresAt?.slice(0, 16) ?? ""}
                onChange={(e) => setState((s) => ({ ...s, schedule: { ...s.schedule, expiresAt: e.target.value ? new Date(e.target.value).toISOString() : undefined } }))}
              />
            </Field>
          </CardContent>
        </Card>
      )}

      {step === 4 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Review & launch</CardTitle></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3 text-sm">
              <Summary label="Name" value={state.name} />
              <Summary label="Type / Priority" value={`${state.type} · ${state.priority}`} />
              <Summary label="Organization" value={orgQ.data?.find((o) => o.id === state.organizationId)?.name ?? "—"} />
              <Summary label="Audience groups" value={String(state.audienceGroupIds.length)} />
              <Summary label="Estimated reach" value={estimatedReach.toLocaleString()} />
              <Summary label="Languages" value={state.languages.map((l) => l.toUpperCase()).join(", ") || "—"} />
              <Summary label="Template" value={selectedTemplate?.name ?? "—"} />
              <Summary label="Schedule" value={
                state.schedule.mode === "schedule"
                  ? `${new Date(state.schedule.startAt ?? "").toLocaleString()} (${state.schedule.timezone})`
                  : state.schedule.mode.replace("_", " ")
              } />
            </div>
            <div className="space-y-2">
              {Object.keys(errors).length === 0 ? (
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-700 dark:text-emerald-400">
                  All checks passed — you're ready to {state.schedule.mode === "publish_now" ? "launch" : "save"}.
                </div>
              ) : (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-700 dark:text-amber-400">
                  <p className="font-semibold">Please resolve before submitting:</p>
                  <ul className="mt-1 list-inside list-disc">
                    {Object.entries(errors).map(([k, v]) => (
                      <li key={k}>{v}</li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="rounded-lg border bg-muted/30 p-4 text-xs text-muted-foreground">
                <p className="text-foreground font-semibold">Estimated delivery</p>
                <p className="mt-1">
                  ~ {(estimatedReach * state.languages.length).toLocaleString()} localized messages across selected channels.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex items-center justify-between gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => (step === 0 ? onCancel?.() : setStep((s) => (Math.max(0, s - 1) as StepIdx)))}
          className="gap-1"
        >
          <ChevronLeft className="h-4 w-4" /> {step === 0 ? "Cancel" : "Back"}
        </Button>
        <div className="flex items-center gap-2">
          {step < 4 ? (
            <Button
              type="button"
              onClick={() => canAdvance(step) && setStep((s) => (Math.min(4, s + 1) as StepIdx))}
              disabled={!canAdvance(step)}
              className="gap-1"
            >
              Next <ChevronRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button type="submit" disabled={saving || Object.keys(errors).length > 0}>
              {saving ? "Saving…" : submitLabel}
            </Button>
          )}
        </div>
      </div>
    </form>
  );
}

function Field({ label, required, error, children, className }: { label: string; required?: boolean; error?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <Label className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </Label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-md border bg-card px-3 py-2">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground text-right">{value || "—"}</span>
    </div>
  );
}
