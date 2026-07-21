import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Search } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { LanguageBadge } from "@/components/common/language-badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { historyService } from "@/services/history.service";

export const Route = createFileRoute("/_authenticated/ai/history")({
  component: AiHistoryPage,
});

function AiHistoryPage() {
  const [search, setSearch] = useState("");
  const history = useQuery({
    queryKey: ["ai-history-list", { search }],
    queryFn: () => historyService.list({ search, pageSize: 50 }),
  });

  return (
    <div className="space-y-5">
        <SectionHeader
          title="AI history"
          description="Every AI-generated draft, preserved for audit and reuse."
        />
        <Card>
          <CardContent className="p-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search history…"
                className="pl-9"
              />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Language</TableHead>
                  <TableHead>Author</TableHead>
                  <TableHead>Versions</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(history.data?.data ?? []).map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="font-medium">{entry.title}</TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-[10px]">
                        {entry.contentType.replace(/_/g, " ")}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <LanguageBadge code={entry.language} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {entry.createdBy}
                    </TableCell>
                    <TableCell>{entry.versions}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDistanceToNow(new Date(entry.createdAt))} ago
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
  );
}
