import { useCallback, useRef, useState } from "react";
import { UploadCloud, X, FileText, Image as ImageIcon, RotateCcw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { uploadService, type UploadItem, type UploadKind } from "@/services/upload.service";

interface UploadManagerProps {
  kind?: UploadKind;
  multiple?: boolean;
  onComplete?: (items: UploadItem[]) => void;
  className?: string;
}

export function UploadManager({
  kind = "document",
  multiple = true,
  onComplete,
  className,
}: UploadManagerProps) {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const enqueue = useCallback(
    async (files: FileList | File[]) => {
      const list = Array.from(files);
      const now = new Date().toISOString();
      const newItems: UploadItem[] = list.map((file) => {
        const error = uploadService.validate(file, kind);
        return {
          id: `up-${Math.random().toString(36).slice(2, 8)}`,
          file,
          kind,
          status: error ? "failed" : "queued",
          progress: 0,
          errorMessage: error ?? undefined,
          startedAt: now,
        };
      });
      setItems((prev) => [...prev, ...newItems]);

      for (const item of newItems) {
        if (item.status === "failed") continue;
        setItems((prev) =>
          prev.map((i) => (i.id === item.id ? { ...i, status: "uploading" } : i)),
        );
        try {
          await uploadService.upload(item.file, (progress) => {
            setItems((prev) =>
              prev.map((i) => (i.id === item.id ? { ...i, progress } : i)),
            );
          });
          setItems((prev) =>
            prev.map((i) =>
              i.id === item.id
                ? {
                    ...i,
                    status: "completed",
                    progress: 100,
                    completedAt: new Date().toISOString(),
                  }
                : i,
            ),
          );
        } catch (error) {
          setItems((prev) =>
            prev.map((i) =>
              i.id === item.id
                ? {
                    ...i,
                    status: "failed",
                    errorMessage: (error as Error).message,
                  }
                : i,
            ),
          );
        }
      }
      onComplete?.(newItems);
    },
    [kind, onComplete],
  );

  const Icon = kind === "image" ? ImageIcon : FileText;

  return (
    <div className={cn("space-y-3", className)}>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void enqueue(e.dataTransfer.files);
        }}
        className={cn(
          "flex w-full flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border/70 bg-muted/20 px-6 py-10 text-sm text-muted-foreground transition-colors hover:border-primary/50 hover:bg-muted/40",
          dragging && "border-primary bg-primary/5 text-primary",
        )}
      >
        <UploadCloud className="h-6 w-6" />
        <span className="font-medium text-foreground">
          Drag & drop {kind === "csv" ? "CSV" : `${kind}s`} here
        </span>
        <span className="text-xs">or click to browse</span>
        <input
          ref={inputRef}
          type="file"
          multiple={multiple}
          className="hidden"
          onChange={(e) => {
            if (e.target.files) void enqueue(e.target.files);
            e.target.value = "";
          }}
        />
      </button>

      {items.length > 0 && (
        <div className="space-y-2">
          {items.map((item) => (
            <Card key={item.id}>
              <CardContent className="flex items-center gap-3 p-3">
                <Icon className="h-5 w-5 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">
                    {item.file.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {(item.file.size / 1024).toFixed(1)} KB
                    {item.errorMessage && ` · ${item.errorMessage}`}
                  </p>
                  {(item.status === "uploading" || item.status === "queued") && (
                    <Progress value={item.progress} className="mt-1.5 h-1" />
                  )}
                </div>
                <div className="flex items-center gap-1">
                  {item.status === "failed" && (
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => void enqueue([item.file])}
                      aria-label="Retry"
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                    </Button>
                  )}
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() =>
                      setItems((prev) => prev.filter((i) => i.id !== item.id))
                    }
                    aria-label="Remove"
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
