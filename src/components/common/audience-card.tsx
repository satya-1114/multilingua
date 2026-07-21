import { Link } from "@tanstack/react-router";
import { Mail, Phone, MapPin } from "lucide-react";
import type { AudienceContact } from "@/types/audience";
import { AudienceAvatar } from "@/components/common/audience-avatar";
import { StatusBadge } from "@/components/common/status-badge";
import { Card } from "@/components/ui/card";

interface AudienceCardProps {
  contact: AudienceContact;
}

export function AudienceCard({ contact }: AudienceCardProps) {
  return (
    <Link
      to="/audience/$id"
      params={{ id: contact.id }}
      className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-xl"
    >
      <Card className="shadow-card hover:shadow-lg transition-shadow p-5">
        <div className="flex items-start gap-3">
          <AudienceAvatar name={contact.fullName} src={contact.avatarUrl} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <p className="truncate text-sm font-semibold text-foreground">{contact.fullName}</p>
              <StatusBadge status={contact.status} />
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground truncate">{contact.occupation}</p>
          </div>
        </div>
        <dl className="mt-4 space-y-1.5 text-xs text-muted-foreground">
          <div className="flex items-center gap-2 truncate">
            <Mail className="h-3.5 w-3.5 shrink-0" /> <span className="truncate">{contact.email}</span>
          </div>
          <div className="flex items-center gap-2">
            <Phone className="h-3.5 w-3.5 shrink-0" /> {contact.phone}
          </div>
          <div className="flex items-center gap-2 truncate">
            <MapPin className="h-3.5 w-3.5 shrink-0" /> <span className="truncate">{contact.city}, {contact.state}</span>
          </div>
        </dl>
        {contact.tags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {contact.tags.slice(0, 3).map((t) => (
              <span
                key={t.id}
                className="rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{ background: `${t.color}1a`, color: t.color }}
              >
                {t.name}
              </span>
            ))}
          </div>
        )}
      </Card>
    </Link>
  );
}
