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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { volunteerService } from "@/services/volunteer.service";
import { organizationService } from "@/services/organization.service";
import type { Volunteer } from "@/types/volunteer";

interface OrganizationAssignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  volunteer: Volunteer;
  onSaved?: (v: Volunteer) => void;
}

const NONE = "__none__";

export function OrganizationAssignDialog({
  open,
  onOpenChange,
  volunteer,
  onSaved,
}: OrganizationAssignDialogProps) {
  const [orgId, setOrgId] = useState<string>(volunteer.organizationId ?? NONE);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) setOrgId(volunteer.organizationId ?? NONE);
  }, [open, volunteer.organizationId]);

  const orgsQ = useQuery({
    queryKey: ["organizations", "for-volunteer-assign"],
    queryFn: () => organizationService.list({ pageSize: 200 }),
    enabled: open,
  });

  async function handleSubmit() {
    setSaving(true);
    try {
      const saved = await volunteerService.assignOrganization(
        volunteer.id,
        orgId === NONE ? null : orgId,
      );
      toast.success("Organization updated");
      onSaved?.(saved);
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to assign organization");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Assign organization</DialogTitle>
          <DialogDescription>
            Link {volunteer.fullName} to an organization, or clear the current assignment.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1.5">
          <Label htmlFor="org">Organization</Label>
          <Select value={orgId} onValueChange={setOrgId}>
            <SelectTrigger id="org">
              <SelectValue placeholder="Select organization" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE}>No organization</SelectItem>
              {(orgsQ.data?.items ?? []).map((o) => (
                <SelectItem key={o.id} value={o.id}>
                  {o.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
