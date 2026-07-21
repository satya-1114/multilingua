import type { KnowledgeArticle, Faq, KeyboardShortcut } from "@/types/help";
import { mockArticles, mockFaqs, mockShortcuts } from "@/lib/mock/platform";

const delay = <T>(v: T, ms = 200): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

export const helpService = {
  async articles(search?: string): Promise<KnowledgeArticle[]> {
    if (!search) return delay(mockArticles);
    const q = search.toLowerCase();
    return delay(mockArticles.filter((a) => a.title.toLowerCase().includes(q) || a.excerpt.toLowerCase().includes(q)));
  },
  async faqs(): Promise<Faq[]> { return delay(mockFaqs); },
  async shortcuts(): Promise<KeyboardShortcut[]> { return delay(mockShortcuts); },
  async submitFeedback(_message: string): Promise<void> { return delay(undefined, 240); },
};
