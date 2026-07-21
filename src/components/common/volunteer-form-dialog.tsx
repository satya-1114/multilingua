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
import { Textarea } from "@/components/ui/textarea";
import { volunteerService } from "@/services/volunteer.service";
import { userService } from "@/services/user.service";
import { VOLUNTEER_AVAILABILITY } from "@/constants/rbac";
import { LANGUAGES } from "@/constants/india";
import type { Volunteer, VolunteerStatus } from "@/types/volunteer";

interface VolunteerFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  volunteer?: Volunteer | null;
  onSaved?: (v: Volunteer) => void;
}

const STATUSES: VolunteerStatus[] = ["available", "busy", "on_leave", "inactive"];

export function VolunteerFormDialog({
  open,
  onOpenChange,
  volunteer,
  onSaved,
}: VolunteerFormDialogProps) {
  const editing = Boolean(volunteer);
  const [userId, setUserId] = useState(volunteer?.userId ?? "");
  const [languages, setLanguages] = useState<string[]>(volunteer?.languages ?? []);
  const [skills, setSkills] = useState<string[]>(volunteer?.skills ?? []);
  const [currentLocation, setCurrentLocation] = useState(volunteer?.currentLocation ?? "");
  const [availability, setAvailability] = useState(volunteer?.availability ?? "flexible");
  const [status, setStatus] = useState<VolunteerStatus>(volunteer?.status ?? "available");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setUserId(volunteer?.userId ?? "");
      setLanguages(volunteer?.languages ?? []);
      setSkills(volunteer?.skills ?? []);
      setCurrentLocation(volunteer?.currentLocation ?? "");
      setAvailability(volunteer?.availability ?? "flexible");
      setStatus(volunteer?.status ?? "available");
    }
  }, [open, volunteer]);

  const usersQ = useQuery({
    queryKey: ["users", "for-volunteer-create"],
    queryFn: () => userService.getUsers(),
    enabled: open && !editing,
  });

  async function handleSubmit() {
    if (!editing && !userId) {
      toast.error("Select a user to register as a volunteer.");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        languages,
        skills,
        currentLocation: currentLocation.trim(),
        availability,
        status,
      };
      const saved = editing && volunteer
        ? await volunteerService.update(volunteer.id, payload)
        : await volunteerService.create({ userId, ...payload });
      toast.success(editing ? "Volunteer updated" : "Volunteer created");
      onSaved?.(saved);
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save volunteer");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit volunteer" : "New volunteer"}</DialogTitle>
          <DialogDescription>
            {editing
              ? "Update this volunteer's profile, skills, and availability."
              : "Register an existing platform user as a volunteer."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {!editing && (
            <div className="space-y-1.5">
              <Label htmlFor="v-user">User</Label>
              <Select value={userId} onValueChange={setUserId}>
                <SelectTrigger id="v-user">
                  <SelectValue placeholder="Select a user" />
                </SelectTrigger>
                <SelectContent>
                  {(usersQ.data ?? []).map((u) => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.fullName} · {u.email}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="v-lang">Languages</Label>
            <Textarea
              id="v-lang"
              rows={2}
              value={languages.join(", ")}
              onChange={(e) =>
                setLanguages(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))
              }
              placeholder={`Comma separated (e.g. ${LANGUAGES.slice(0, 3).map((l) => l.code).join(", ")})`}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="v-skills">Skills</Label>
            <Textarea
              id="v-skills"
              rows={2}
              value={skills.join(", ")}
              onChange={(e) =>
                setSkills(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))
              }
              placeholder="Comma separated (e.g. logistics, first-aid)"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="v-loc">Location</Label>
              <Input
                id="v-loc"
                value={currentLocation}
                onChange={(e) => setCurrentLocation(e.target.value)}
                placeholder="City / ward"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="v-avail">Availability</Label>
              <Select value={availability} onValueChange={setAvailability}>
                <SelectTrigger id="v-avail"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {VOLUNTEER_AVAILABILITY.map((a) => (
                    <SelectItem key={a} value={a}>{a}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="v-status">Status</Label>
            <Select value={status} onValueChange={(v) => setStatus(v as VolunteerStatus)}>
              <SelectTrigger id="v-status"><SelectValue /></SelectTrigger>
              <SelectContent>
                {STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>{s.replace("_", " ")}</SelectItem>
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
            {saving ? "Saving…" : editing ? "Save changes" : "Create volunteer"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
