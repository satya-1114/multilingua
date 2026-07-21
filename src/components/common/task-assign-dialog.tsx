import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { taskService } from "@/services/task.service";
import { campaignService } from "@/services/campaign.service";
import type {
  TaskPriority,
  VolunteerTask,
} from "@/types/volunteer";

interface TaskAssignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  volunteerId: string;
  volunteerName?: string;
  task?: VolunteerTask | null;
  onSaved?: (task: VolunteerTask) => void;
}

const PRIORITIES: TaskPriority[] = ["low", "medium", "high", "urgent"];

export function TaskAssignDialog({
  open,
  onOpenChange,
  volunteerId,
  volunteerName,
  task,
  onSaved,
}: TaskAssignDialogProps) {
  const editing = Boolean(task);
  const [campaignId, setCampaignId] = useState(task?.campaignId ?? "");
  const [title, setTitle] = useState(task?.title ?? "");
  const [description, setDescription] = useState(task?.description ?? "");
  const [priority, setPriority] = useState<TaskPriority>(task?.priority ?? "medium");
  const [dueAt, setDueAt] = useState(task?.dueAt?.slice(0, 10) ?? "");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setCampaignId(task?.campaignId ?? "");
      setTitle(task?.title ?? "");
      setDescription(task?.description ?? "");
      setPriority(task?.priority ?? "medium");
      setDueAt(task?.dueAt?.slice(0, 10) ?? "");
    }
  }, [open, task]);

  const campaignsQuery = useQuery({
    queryKey: ["campaigns", "for-task-assign"],
    queryFn: () => campaignService.listAll({}),
    enabled: open,
  });

  async function handleSubmit() {
    if (!title.trim() || !campaignId) {
      toast.error("Campaign and title are required.");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        volunteerId,
        campaignId,
        title: title.trim(),
        description: description.trim(),
        priority,
        dueAt: dueAt ? new Date(dueAt).toISOString() : undefined,
      };
      const saved = editing && task
        ? await taskService.update(task.id, payload)
        : await taskService.assign(payload);
      toast.success(editing ? "Task updated" : "Task assigned");
      onSaved?.(saved);
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save task");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit assignment" : "Assign task"}</DialogTitle>
          <DialogDescription>
            {volunteerName ? `Assign a task to ${volunteerName}.` : "Assign a task to this volunteer."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="campaign">Campaign</Label>
            <Select value={campaignId} onValueChange={setCampaignId}>
              <SelectTrigger id="campaign">
                <SelectValue placeholder="Select a campaign" />
              </SelectTrigger>
              <SelectContent>
                {(campaignsQuery.data ?? []).map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="title">Task title</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Distribute flyers in Ward 5"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="priority">Priority</Label>
              <Select value={priority} onValueChange={(v) => setPriority(v as TaskPriority)}>
                <SelectTrigger id="priority">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PRIORITIES.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="due">Due date</Label>
              <Input id="due" type="date" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={saving}>
            {saving ? "Saving…" : editing ? "Save changes" : "Assign task"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
