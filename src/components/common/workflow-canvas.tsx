import { useMemo, useState } from "react";
import { Minus, Plus, RotateCcw, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { WorkflowNodeCard } from "./workflow-node";
import type { Workflow } from "@/types/automation";

interface WorkflowCanvasProps {
  workflow: Workflow;
  selectedId?: string;
  onSelect?: (id: string) => void;
}

export function WorkflowCanvas({ workflow, selectedId, onSelect }: WorkflowCanvasProps) {
  const [zoom, setZoom] = useState(1);
  const width = 1000;
  const height = 400;

  const edges = useMemo(() => {
    return workflow.edges
      .map((e) => {
        const a = workflow.nodes.find((n) => n.id === e.from);
        const b = workflow.nodes.find((n) => n.id === e.to);
        if (!a || !b) return null;
        const x1 = a.x + 176;
        const y1 = a.y + 40;
        const x2 = b.x;
        const y2 = b.y + 40;
        const midX = (x1 + x2) / 2;
        return { id: e.id, d: `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}` };
      })
      .filter(Boolean) as { id: string; d: string }[];
  }, [workflow.edges, workflow.nodes]);

  return (
    <Card className="relative overflow-hidden">
      <div className="flex items-center justify-between border-b px-3 py-2">
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <span>Zoom</span>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))}>
            <Minus className="h-3.5 w-3.5" />
          </Button>
          <span className="w-10 text-center font-mono">{Math.round(zoom * 100)}%</span>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setZoom((z) => Math.min(1.5, z + 0.1))}>
            <Plus className="h-3.5 w-3.5" />
          </Button>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" className="h-7 gap-1 text-xs">
            <RotateCcw className="h-3.5 w-3.5" /> Undo
          </Button>
          <Button variant="ghost" size="sm" className="h-7 gap-1 text-xs">
            <RotateCw className="h-3.5 w-3.5" /> Redo
          </Button>
        </div>
      </div>
      <div className="relative overflow-auto bg-muted/20" style={{ height: 440 }}>
        <div style={{ width, height, transform: `scale(${zoom})`, transformOrigin: "0 0" }} className="relative">
          <svg width={width} height={height} className="absolute inset-0 pointer-events-none">
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="hsl(var(--muted-foreground))" />
              </marker>
            </defs>
            {edges.map((e) => (
              <path key={e.id} d={e.d} stroke="hsl(var(--muted-foreground))" strokeWidth={1.5} fill="none" markerEnd="url(#arrow)" />
            ))}
          </svg>
          {workflow.nodes.map((n) => (
            <WorkflowNodeCard
              key={n.id}
              kind={n.kind}
              title={n.title}
              description={n.description}
              selected={selectedId === n.id}
              onClick={() => onSelect?.(n.id)}
              style={{ left: n.x, top: n.y }}
            />
          ))}
        </div>
        <div className="pointer-events-none absolute bottom-3 right-3 rounded-lg border bg-background/90 p-2 shadow-card">
          <p className="mb-1 text-[10px] font-semibold uppercase text-muted-foreground">Overview</p>
          <div className="relative h-16 w-32 rounded border bg-muted/30">
            {workflow.nodes.map((n) => (
              <div
                key={n.id}
                className="absolute h-2 w-2 rounded-sm bg-primary/70"
                style={{ left: (n.x / width) * 128, top: (n.y / height) * 64 }}
              />
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}
