import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Search, Send } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { KnowledgeCard } from "@/components/common/knowledge-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { helpService } from "@/services/help.service";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/help")({
  head: () => ({ meta: [{ title: "Help center" }, { name: "robots", content: "noindex" }] }),
  component: HelpPage,
});

function HelpPage() {
  const [q, setQ] = useState("");
  const [feedback, setFeedback] = useState("");
  const articles = useQuery({ queryKey: ["help", "articles", q], queryFn: () => helpService.articles(q) });
  const faqs = useQuery({ queryKey: ["help", "faqs"], queryFn: () => helpService.faqs() });
  const submit = useMutation({
    mutationFn: (m: string) => helpService.submitFeedback(m),
    onSuccess: () => {
      setFeedback("");
      toast.success("Thanks — your feedback was sent to the product team.");
    },
  });

  return (
    <div className="space-y-5">
        <SectionHeader title="Help center" description="Guides, FAQs, and support for the platform." />

        <Card>
          <CardContent className="p-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search knowledge base…" className="pl-10 text-base" />
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(articles.data ?? []).map((a) => <KnowledgeCard key={a.id} article={a} />)}
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle className="text-base">Frequently asked</CardTitle></CardHeader>
            <CardContent>
              <Accordion type="single" collapsible>
                {(faqs.data ?? []).map((f) => (
                  <AccordionItem key={f.id} value={f.id}>
                    <AccordionTrigger className="text-sm">{f.question}</AccordionTrigger>
                    <AccordionContent className="text-sm text-muted-foreground">{f.answer}</AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Contact support</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Send a message to the platform team. Response within one business day.
              </p>
              <Textarea rows={5} value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="Describe your question or issue…" />
              <Button onClick={() => submit.mutate(feedback)} disabled={!feedback.trim() || submit.isPending}>
                <Send className="mr-1 h-4 w-4" /> Send feedback
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
  );
}
