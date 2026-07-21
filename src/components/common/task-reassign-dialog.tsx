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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { taskService } from "@/services/task.service";
import { volunteerService } from "@/services/volunteer.service";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import type { VolunteerTask } from "@/types/volunteer";

interface TaskReassignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task: VolunteerTask;
  onSaved?: (t: VolunteerTask) => void;
}

export function TaskReassignDialog({
  open,
  onOpenChange,
  task,
  onSaved,
}: TaskReassignDialogProps) {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 250);
  const [volunteerId, setVolunteerId] = useState<string>(task.volunteerId);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setSearch("");
      setVolunteerId(task.volunteerId);
    }
  }, [open, task.volunteerId]);

  const volunteersQ = useQuery({
    queryKey: ["volunteers", "for-reassign", debouncedSearch],
    queryFn: () =>
      volunteerService.list({
        search: debouncedSearch || undefined,
        status: "available",
        pageSize: 25,
      }),
    enabled: open,
  });

  async function handleSubmit() {
    if (!volunteerId || volunteerId === task.volunteerId) {
      toast.error("Pick a different volunteer to reassign.");
      return;
    }
    setSaving(true);
    try {
      const saved = await taskService.reassign(task.id, volunteerId);
      toast.success("Task reassigned");
      onSaved?.(saved);
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to reassign task");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Reassign task</DialogTitle>
          <DialogDescription>
            Move &ldquo;{task.title}&rdquo; to another available volunteer.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="reassign-search">Search volunteers</Label>
            <Input
              id="reassign-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or email"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="reassign-select">Volunteer</Label>
            <Select value={volunteerId} onValueChange={setVolunteerId}>
              <SelectTrigger id="reassign-select">
                <SelectValue placeholder="Select volunteer" />
              </SelectTrigger>
              <SelectContent>
                {(volunteersQ.data?.items ?? []).map((v) => (
                  <SelectItem key={v.id} value={v.id}>
                    {v.fullName} · {v.status}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={saving}>
            {saving ? "Saving…" : "Reassign"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
