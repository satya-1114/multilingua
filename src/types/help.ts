export interface KnowledgeArticle {
  id: string;
  title: string;
  category: string;
  excerpt: string;
  body: string;
  updatedAt: string;
  readMinutes: number;
}

export interface Faq {
  id: string;
  question: string;
  answer: string;
  category: string;
}

export interface KeyboardShortcut {
  keys: string[];
  description: string;
  category: string;
}
