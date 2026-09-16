import type { ChatMessage } from "./types";

/**
 * Follow-up suggestions, derived client-side.
 *
 * Deliberately NOT model-generated: asking the LLM for follow-ups would add
 * a second generation to every grounded turn, which on the local Ollama path
 * costs another 20-40s per answer -- a bad trade for a convenience feature.
 * These are instead keyed off the episodes the answer actually cited, so a
 * suggestion only ever points at a topic the corpus genuinely covers and
 * can therefore answer in a grounded way.
 *
 * Suggestions the user has already asked in this session are filtered out.
 */

const BY_SOURCE: Record<string, string[]> = {
  "Finding Product-Market Fit Before You Run Out of Runway": [
    "What retention curve shape signals real product-market fit?",
    "How long should we give ourselves before pivoting?",
    "Is the Sean Ellis test still worth running?",
  ],
  "Growth Loops vs. Funnels: Why Compounding Beats Acquisition": [
    "How do I pick which growth loop to invest in?",
    "What makes a loop compound instead of decay?",
    "Why do teams default to funnel thinking?",
  ],
  "Activation Metrics and Finding Your Aha Moment": [
    "How do I find our aha moment instead of guessing it?",
    "How do I shorten time-to-first-value?",
    "When should we redefine our activation metric?",
  ],
  "Onboarding Design Principles That Actually Convert": [
    "Should onboarding branch by user intent?",
    "Do onboarding checklists actually help?",
    "How should empty states be designed?",
  ],
  "Pricing and Packaging: The Most Underrated Growth Lever": [
    "How do I choose the right pricing metric?",
    "How should the three tiers actually differ?",
    "How often should we revisit pricing?",
  ],
  "Retention and the Real Cost of a Leaky Bucket": [
    "How do I tell fixable churn from natural attrition?",
    "How should I read a cohort retention curve?",
    "What's an underrated lever for improving retention?",
  ],
  "Product-Led Growth vs. Sales-Led Growth: Choosing Your Motion": [
    "How do I know which motion fits our product?",
    "Can we run PLG and sales-led at the same time?",
    "Where should the handoff to sales happen?",
  ],
  "Building Your First Growth Team": [
    "When should we make our first growth hire?",
    "Generalist or specialist for the first hire?",
    "How do I tell if a growth team has drifted into busywork?",
  ],
  "Positioning and Messaging When Everyone Looks the Same": [
    "How do I find the alternative customers actually use today?",
    "How often should positioning change as we grow?",
    "How do I test whether new positioning is working?",
  ],
  "Prioritization Frameworks for Overwhelmed PMs": [
    "Do RICE and ICE actually work in practice?",
    "How do I prioritize when we have no good data yet?",
    "How do I handle competing stakeholder priorities?",
  ],
};

const GENERIC = [
  "Turn this into a Ship 30 essay",
  "What else does the corpus cover on this?",
  "Summarize this as a shareable doc",
];

function normalize(text: string): string {
  return text.trim().toLowerCase().replace(/\s+/g, " ").replace(/[?.!]+$/, "");
}

/**
 * Suggestions for the latest grounded assistant message.
 * Returns [] when the turn wasn't grounded — offering follow-ups on a
 * "not covered" answer would just invite more unanswerable questions.
 */
export function suggestFollowUps(messages: ChatMessage[], max = 3): string[] {
  const last = [...messages].reverse().find((m) => m.role === "assistant");
  if (!last || last.grounded !== true) return [];

  const asked = new Set(
    messages.filter((m) => m.role === "user").map((m) => normalize(m.content))
  );

  const pool: string[] = [];
  for (const citation of last.citations ?? []) {
    for (const q of BY_SOURCE[citation.title] ?? []) pool.push(q);
  }
  for (const q of GENERIC) pool.push(q);

  const seen = new Set<string>();
  const out: string[] = [];
  for (const q of pool) {
    const key = normalize(q);
    if (asked.has(key) || seen.has(key)) continue;
    seen.add(key);
    out.push(q);
    if (out.length >= max) break;
  }
  return out;
}
