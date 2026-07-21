import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Languages,
  Sparkles,
  Volume2,
  RefreshCw,
  Trash2,
  Save,
  Play,
  Wand2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/common/empty-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { PermissionGuard } from "@/components/common/permission-guard";
import { PERMISSIONS } from "@/constants/rbac";
import { LANGUAGES } from "@/constants/india";
import { multilingualService } from "@/services/multilingual.service";
import type {
  AiVariantKind,
  MultilingualParentType,
  TranslationEntry,
  TranslationStatus,
} from "@/types/multilingual";

/**
 * Reusable multilingual authoring panel.
 *
 * Used inside the existing Campaign and Disaster detail pages. Owns
 * translation authoring, TTS generation, and AI variant tools for one
 * parent entity. No duplicate services, dialogs, or forms — every action
 * routes through `multilingualService`.
 */

interface Props {
  parentType: MultilingualParentType;
  parentId: string;
  supportsSafetyInstructions?: boolean;
}

const SUPPORTED_LANGS = [
  "en", "hi", "te", "ta", "kn", "ml", "bn", "mr", "gu", "pa",
] as const;

const VARIANTS: { kind: AiVariantKind; label: string }[] = [
  { kind: "summary", label: "Summary" },
  { kind: "short_announcement", label: "Short announcement" },
  { kind: "emergency_sms", label: "Emergency SMS" },
  { kind: "social_post", label: "Social media" },
  { kind: "poster_text", label: "Poster text" },
  { kind: "speech_script", label: "Public speech" },
  { kind: "radio_announcement", label: "Radio announcement" },
  { kind: "voice_announcement", label: "Voice announcement" },
];

const STATUS_TONE: Record<TranslationStatus, string> = {
  draft: "bg-muted text-muted-foreground",
  generated: "bg-sky-500/10 text-sky-600",
  edited: "bg-amber-500/10 text-amber-700",
  published: "bg-emerald-500/10 text-emerald-700",
};

function langLabel(code: string) {
  return LANGUAGES.find((l) => l.code === code)?.label ?? code.toUpperCase();
}

export function MultilingualPanel({ parentType, parentId, supportsSafetyInstructions }: Props) {
  const qc = useQueryClient();
  const key = ["multilingual", parentType, parentId];
  const q = useQuery({ queryKey: key, queryFn: () => multilingualService.get(parentType, parentId) });

  const [activeLang, setActiveLang] = useState<string>("");
  const [targetToAdd, setTargetToAdd] = useState<string>("");

  const invalidate = () => qc.invalidateQueries({ queryKey: key });

  const generate = useMutation({
    mutationFn: (targets: string[]) =>
      multilingualService.generate(parentType, parentId, { targetLanguages: targets }),
    onSuccess: () => {
      toast.success("Translation generated");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message ?? "Generation failed"),
  });

  if (q.isLoading) return <SkeletonBlock rows={8} />;
  if (q.isError || !q.data)
    return <ErrorState title="Unable to load translations" onRetry={() => q.refetch()} />;

  const bundle = q.data;
  const entries = bundle.entries;
  const existingLangs = new Set(entries.map((e) => e.language));
  const availableToAdd = SUPPORTED_LANGS.filter((c) => !existingLangs.has(c));
  const currentLang = activeLang || bundle.sourceLanguage;
  const current = entries.find((e) => e.language === currentLang) ?? entries[0];

  return (
    <div className="space-y-4">
      <Card className="shadow-card">
        <CardHeader className="flex flex-row items-center justify-between gap-2 pb-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Languages className="h-4 w-4" /> Multilingual content
            </CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              Source language: {langLabel(bundle.sourceLanguage)} · {entries.length} language
              {entries.length === 1 ? "" : "s"}
            </p>
          </div>
          <PermissionGuard anyOf={[PERMISSIONS.AI_GENERATE, PERMISSIONS.TRANSLATION_USE]}>
            <div className="flex items-center gap-2">
              <Select value={targetToAdd} onValueChange={setTargetToAdd}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Add language" />
                </SelectTrigger>
                <SelectContent>
                  {availableToAdd.length === 0 ? (
                    <div className="p-2 text-xs text-muted-foreground">All languages added</div>
                  ) : (
                    availableToAdd.map((code) => (
                      <SelectItem key={code} value={code}>{langLabel(code)}</SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              <Button
                size="sm"
                disabled={!targetToAdd || generate.isPending}
                onClick={() => {
                  generate.mutate([targetToAdd]);
                  setTargetToAdd("");
                }}
              >
                <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                Generate
              </Button>
            </div>
          </PermissionGuard>
        </CardHeader>
        <CardContent>
          {entries.length === 0 ? (
            <EmptyState
              title="No translations yet"
              description="Generate the first translation to publish this content in additional languages."
            />
          ) : (
            <Tabs value={currentLang} onValueChange={setActiveLang}>
              <TabsList className="flex flex-wrap">
                {entries.map((e) => (
                  <TabsTrigger key={e.language} value={e.language} className="gap-1.5">
                    {langLabel(e.language)}
                    <Badge variant="secondary" className={`ml-1 ${STATUS_TONE[e.status]}`}>
                      {e.status}
                    </Badge>
                  </TabsTrigger>
                ))}
              </TabsList>
              {entries.map((e) => (
                <TabsContent key={e.language} value={e.language} className="pt-4">
                  <TranslationEditor
                    parentType={parentType}
                    parentId={parentId}
                    entry={e}
                    isSource={e.language === bundle.sourceLanguage}
                    supportsSafetyInstructions={supportsSafetyInstructions}
                    onChanged={invalidate}
                  />
                </TabsContent>
              ))}
            </Tabs>
          )}
        </CardContent>
      </Card>

      {current && (
        <VariantsCard
          parentType={parentType}
          parentId={parentId}
          entry={current}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */

function TranslationEditor({
  parentType,
  parentId,
  entry,
  isSource,
  supportsSafetyInstructions,
  onChanged,
}: {
  parentType: MultilingualParentType;
  parentId: string;
  entry: TranslationEntry;
  isSource: boolean;
  supportsSafetyInstructions?: boolean;
  onChanged: () => void;
}) {
  const [title, setTitle] = useState(entry.title ?? "");
  const [content, setContent] = useState(entry.content);
  const [safety, setSafety] = useState(entry.safetyInstructions ?? "");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [confirmAudioDelete, setConfirmAudioDelete] = useState(false);

  const dirty = useMemo(
    () =>
      title !== (entry.title ?? "") ||
      content !== entry.content ||
      safety !== (entry.safetyInstructions ?? ""),
    [title, content, safety, entry],
  );

  const save = useMutation({
    mutationFn: (status?: TranslationStatus) =>
      multilingualService.update(parentType, parentId, {
        language: entry.language,
        title,
        content,
        safetyInstructions: supportsSafetyInstructions ? safety : undefined,
        status,
      }),
    onSuccess: () => {
      toast.success("Translation saved");
      onChanged();
    },
    onError: (e: Error) => toast.error(e.message ?? "Save failed"),
  });

  const regenerate = useMutation({
    mutationFn: () => multilingualService.regenerate(parentType, parentId, entry.language),
    onSuccess: () => {
      toast.success("Regenerated");
      onChanged();
    },
    onError: (e: Error) => toast.error(e.message ?? "Regenerate failed"),
  });

  const remove = useMutation({
    mutationFn: () => multilingualService.remove(parentType, parentId, entry.language),
    onSuccess: () => {
      toast.success("Translation deleted");
      onChanged();
    },
    onError: (e: Error) => toast.error(e.message ?? "Delete failed"),
  });

  const generateAudio = useMutation({
    mutationFn: (replace: boolean) =>
      multilingualService.generateAudio(parentType, parentId, {
        language: entry.language,
        replace,
      }),
    onSuccess: () => {
      toast.success("Audio ready");
      onChanged();
    },
    onError: (e: Error) => toast.error(e.message ?? "TTS failed"),
  });

  const removeAudio = useMutation({
    mutationFn: () => multilingualService.removeAudio(parentType, parentId, entry.language),
    onSuccess: () => {
      toast.success("Audio deleted");
      onChanged();
    },
    onError: (e: Error) => toast.error(e.message ?? "Delete failed"),
  });

  return (
    <div className="space-y-4">
      <div className="grid gap-3">
        <div>
          <Label htmlFor={`title-${entry.language}`}>Title</Label>
          <Input
            id={`title-${entry.language}`}
            value={title}
            onChange={(ev) => setTitle(ev.target.value)}
          />
        </div>
        <div>
          <Label htmlFor={`body-${entry.language}`}>Content</Label>
          <Textarea
            id={`body-${entry.language}`}
            rows={8}
            value={content}
            onChange={(ev) => setContent(ev.target.value)}
          />
        </div>
        {supportsSafetyInstructions && (
          <div>
            <Label htmlFor={`safety-${entry.language}`}>Safety instructions</Label>
            <Textarea
              id={`safety-${entry.language}`}
              rows={4}
              value={safety}
              onChange={(ev) => setSafety(ev.target.value)}
            />
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3">
        <PermissionGuard anyOf={[PERMISSIONS.CONTENT_EDIT]}>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              disabled={!dirty || save.isPending}
              onClick={() => save.mutate("edited")}
            >
              <Save className="mr-1.5 h-3.5 w-3.5" /> Save
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={save.isPending}
              onClick={() => save.mutate("published")}
            >
              Publish
            </Button>
            {!isSource && (
              <>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={regenerate.isPending}
                  onClick={() => regenerate.mutate()}
                >
                  <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Regenerate
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-destructive"
                  onClick={() => setConfirmDelete(true)}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" /> Delete
                </Button>
              </>
            )}
          </div>
        </PermissionGuard>

        <PermissionGuard anyOf={[PERMISSIONS.AI_GENERATE]}>
          <div className="flex flex-wrap items-center gap-2">
            {entry.audio ? (
              <>
                {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                <audio src={entry.audio.url} controls className="h-8" />
                <Button
                  size="sm"
                  variant="outline"
                  disabled={generateAudio.isPending}
                  onClick={() => generateAudio.mutate(true)}
                >
                  <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Replace audio
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-destructive"
                  onClick={() => setConfirmAudioDelete(true)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </>
            ) : (
              <Button
                size="sm"
                variant="outline"
                disabled={generateAudio.isPending}
                onClick={() => generateAudio.mutate(false)}
              >
                <Volume2 className="mr-1.5 h-3.5 w-3.5" /> Generate audio
              </Button>
            )}
          </div>
        </PermissionGuard>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title={`Delete ${langLabel(entry.language)} translation?`}
        description="The translated text and its audio will be removed. The source content is not affected."
        confirmLabel="Delete"
        onConfirm={() => remove.mutate()}
      />
      <ConfirmDialog
        open={confirmAudioDelete}
        onOpenChange={setConfirmAudioDelete}
        title="Delete generated audio?"
        description="The audio file will be removed. The translated text is not affected."
        confirmLabel="Delete audio"
        onConfirm={() => removeAudio.mutate()}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */

function VariantsCard({
  parentType,
  parentId,
  entry,
}: {
  parentType: MultilingualParentType;
  parentId: string;
  entry: TranslationEntry;
}) {
  const qc = useQueryClient();
  const [busy, setBusy] = useState<AiVariantKind | null>(null);

  async function generate(kind: AiVariantKind) {
    setBusy(kind);
    try {
      await multilingualService.generateVariant(parentType, parentId, {
        language: entry.language,
        kind,
      });
      qc.invalidateQueries({ queryKey: ["multilingual", parentType, parentId] });
      toast.success("Variant generated");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "AI generation failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card className="shadow-card">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Wand2 className="h-4 w-4" /> AI content tools · {langLabel(entry.language)}
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          AI-assisted variants for the selected language. These do not replace the primary
          translated content.
        </p>
      </CardHeader>
      <CardContent>
        <PermissionGuard
          anyOf={[PERMISSIONS.AI_GENERATE]}
          fallback={
            <p className="text-sm text-muted-foreground">
              AI tools are available to Campaign Managers.
            </p>
          }
        >
          <div className="grid gap-3 sm:grid-cols-2">
            {VARIANTS.map((v) => {
              const existing = entry.variants?.[v.kind];
              return (
                <div key={v.kind} className="rounded-md border p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">{v.label}</span>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busy !== null}
                      onClick={() => generate(v.kind)}
                    >
                      {existing ? (
                        <>
                          <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Regenerate
                        </>
                      ) : (
                        <>
                          <Sparkles className="mr-1.5 h-3.5 w-3.5" /> Generate
                        </>
                      )}
                    </Button>
                  </div>
                  {existing ? (
                    <p className="whitespace-pre-wrap text-xs text-muted-foreground">{existing}</p>
                  ) : (
                    <p className="text-xs italic text-muted-foreground">Not generated yet.</p>
                  )}
                </div>
              );
            })}
          </div>
        </PermissionGuard>
      </CardContent>
    </Card>
  );
}

/* Re-export for downstream consumers that want the icon set. */
export { Play };
