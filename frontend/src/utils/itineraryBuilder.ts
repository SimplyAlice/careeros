import type { DecisionCandidateRead, InformationCategory } from '../types/planning';

export interface ProposedItineraryItem {
  candidate: DecisionCandidateRead;
  icon: string;
  subtitle: string;
  costNumber: number;
  rationale: string[];
}

export interface ProposedItinerary {
  items: ProposedItineraryItem[];
  alternatives: DecisionCandidateRead[];
  estimatedTotal: number;
  remainingBudget: number | null;
  isOverBudget: boolean;
  narrativeSubheading: string;
}

/**
 * Category icons for consumer editorial feel.
 */
export const CATEGORY_ICONS: Record<InformationCategory | string, string> = {
  nature: '🌿',
  culture: '🎨',
  food: '🍽️',
  entertainment: '🎟️',
  wellness: '🧘',
  shopping: '🛍️',
};

export function getCategoryIcon(category: string): string {
  return CATEGORY_ICONS[category.toLowerCase()] || '✨';
}

/**
 * Parses numeric cost from string/number safely.
 */
export function parseCandidateCost(cost: string | number | null | undefined): number {
  if (cost === null || cost === undefined) return 0;
  if (typeof cost === 'number') return cost;
  const parsed = parseFloat(cost);
  return isNaN(parsed) ? 0 : parsed;
}

/**
 * Formats a clean subtitle for an itinerary card.
 */
export function buildItemSubtitle(candidate: DecisionCandidateRead): string {
  const parts: string[] = [];

  const categoryName = candidate.category.charAt(0).toUpperCase() + candidate.category.slice(1);
  parts.push(categoryName);

  if (candidate.duration_minutes) {
    parts.push(`${candidate.duration_minutes}m`);
  } else if (candidate.option_type === 'place') {
    parts.push('Flexible time');
  }

  if (candidate.location) {
    parts.push(candidate.location);
  }

  return parts.join(' · ');
}

/**
 * Formats currency in South African Rands or Free.
 */
export function formatCurrency(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined) return 'Free';
  const num = typeof amount === 'number' ? amount : parseFloat(amount);
  if (isNaN(num) || num === 0) return 'Free';
  return `R${num.toFixed(0)}`;
}

/**
 * Humanizes backend machine decision reasons into warm, conversational explanations.
 * Eliminates machine scores, internal IDs, and technical provenance.
 */
export function humanizeCandidateReasons(
  candidate: DecisionCandidateRead,
  budgetMax: number | null,
  groupSize: number = 1
): string[] {
  const humanReasons: string[] = [];
  const cost = parseCandidateCost(candidate.cost);

  // 1. Budget rationale
  if (cost === 0) {
    humanReasons.push('Free to enjoy — zero impact on your budget.');
  } else if (budgetMax !== null && cost <= budgetMax) {
    humanReasons.push(`Fits comfortably within your ${formatCurrency(budgetMax)} budget.`);
  }

  // 2. Group suitability
  if (groupSize > 1) {
    humanReasons.push(`Well suited for a group of ${groupSize}.`);
  }

  // 3. Category context
  if (candidate.category === 'nature') {
    humanReasons.push('Offers a scenic, relaxed outdoor start.');
  } else if (candidate.category === 'culture') {
    humanReasons.push('Adds a rich cultural dimension to your plan.');
  } else if (candidate.category === 'food') {
    humanReasons.push('Great spot for group conversation and food.');
  }

  // Fallback to any positive message from backend reasons if human list is small
  if (humanReasons.length < 2 && candidate.reasons) {
    for (const r of candidate.reasons) {
      if (r.outcome === 'supported' && r.message) {
        // Strip machine jargon if present
        const cleanMsg = r.message.replace(/R0\.00/g, 'R0');
        if (!humanReasons.includes(cleanMsg)) {
          humanReasons.push(cleanMsg);
        }
      }
    }
  }

  return humanReasons.slice(0, 3);
}

/**
 * Calculates trade-off note when comparing an alternative candidate to a current slot.
 */
export function getTradeOffNote(
  altCandidate: DecisionCandidateRead,
  currentCandidate?: DecisionCandidateRead
): string {
  const altCost = parseCandidateCost(altCandidate.cost);
  if (!currentCandidate) {
    return formatCurrency(altCost);
  }

  const currentCost = parseCandidateCost(currentCandidate.cost);
  const diff = altCost - currentCost;

  if (diff < 0) {
    return `Saves ${formatCurrency(Math.abs(diff))}`;
  } else if (diff > 0) {
    return `+${formatCurrency(diff)} more`;
  }
  return `Same cost (${formatCurrency(altCost)})`;
}

/**
 * Builds a natural, conversational narrative subheading for the proposed plan.
 */
export function buildProposalNarrative(
  items: ProposedItineraryItem[],
  _budgetMax: number | null,
  remainingBudget: number | null
): string {
  const categories = new Set(items.map((i) => i.candidate.category));

  if (categories.has('food') && (categories.has('nature') || categories.has('culture'))) {
    if (remainingBudget !== null && remainingBudget > 0) {
      return `A balanced plan with something fun to do, good food, and ${formatCurrency(remainingBudget)} left in your budget.`;
    }
    return 'A balanced plan with something fun to do and great food.';
  }

  if (categories.has('food')) {
    return 'A delicious, food-forward experience tailored to your group.';
  }

  if (categories.has('culture') || categories.has('nature')) {
    return 'A scenic, engaging day out designed to match your pace.';
  }

  return 'A thoughtful sequence designed to make the most of your time and budget.';
}

/**
 * Assembles a coherent proposed itinerary from ranked recommendation candidates.
 *
 * Intent-aware and extensible:
 * - Prioritizes requested themes (food, outdoors, culture) when present.
 * - Otherwise builds a varied, non-repetitive sequence across categories.
 * - Strictly enforces budget limits.
 */
export function buildProposedItinerary(
  candidates: DecisionCandidateRead[],
  budgetMax: number | null,
  intentText: string = '',
  groupSize: number = 1
): ProposedItinerary {
  const eligible = candidates.filter((c) => c.is_eligible);
  if (eligible.length === 0) {
    return {
      items: [],
      alternatives: [],
      estimatedTotal: 0,
      remainingBudget: budgetMax,
      isOverBudget: false,
      narrativeSubheading: 'Explore options to build your plan.',
    };
  }

  const lowerIntent = intentText.toLowerCase();
  const isFoodFocused = /food|eat|dinner|lunch|tasting|restaurant|drinks|cocktail/.test(lowerIntent);
  const isOutdoorsFocused = /outdoor|nature|walk|hike|park|garden|beach/.test(lowerIntent);
  const isCultureFocused = /culture|cultural|history|museum|art|heritage/.test(lowerIntent);

  const selectedCandidates: DecisionCandidateRead[] = [];
  const selectedOptionIds = new Set<string>();
  const selectedCategories = new Set<string>();
  let currentCost = 0;

  // 1. If user has a strong focus, pick top candidate from that category first
  if (isFoodFocused || isOutdoorsFocused || isCultureFocused) {
    const focusedCategory = isFoodFocused ? 'food' : isOutdoorsFocused ? 'nature' : 'culture';
    const focusMatch = eligible.find((c) => c.category === focusedCategory);
    if (focusMatch) {
      const cost = parseCandidateCost(focusMatch.cost);
      if (budgetMax === null || cost <= budgetMax) {
        selectedCandidates.push(focusMatch);
        selectedOptionIds.add(focusMatch.option_id);
        selectedCategories.add(focusMatch.category);
        currentCost += cost;
      }
    }
  }

  // 2. Add candidates with category diversity up to 3 items, staying within budget
  const maxItems = 3;
  for (const candidate of eligible) {
    if (selectedCandidates.length >= maxItems) break;
    if (selectedOptionIds.has(candidate.option_id)) continue;

    const candidateCost = parseCandidateCost(candidate.cost);
    if (budgetMax !== null && currentCost + candidateCost > budgetMax) {
      continue;
    }

    if (!selectedCategories.has(candidate.category) || selectedCandidates.length === 0) {
      selectedCandidates.push(candidate);
      selectedOptionIds.add(candidate.option_id);
      selectedCategories.add(candidate.category);
      currentCost += candidateCost;
    }
  }

  // 3. Fallback: if we still have room and budget, fill with any remaining eligible items
  if (selectedCandidates.length < maxItems) {
    for (const candidate of eligible) {
      if (selectedCandidates.length >= maxItems) break;
      if (selectedOptionIds.has(candidate.option_id)) continue;

      const candidateCost = parseCandidateCost(candidate.cost);
      if (budgetMax !== null && currentCost + candidateCost > budgetMax) {
        continue;
      }

      selectedCandidates.push(candidate);
      selectedOptionIds.add(candidate.option_id);
      currentCost += candidateCost;
    }
  }

  // Map selected candidates to itinerary items with humanized rationale
  const items: ProposedItineraryItem[] = selectedCandidates.map((candidate) => ({
    candidate,
    icon: getCategoryIcon(candidate.category),
    subtitle: buildItemSubtitle(candidate),
    costNumber: parseCandidateCost(candidate.cost),
    rationale: humanizeCandidateReasons(candidate, budgetMax, groupSize),
  }));

  const alternatives = eligible.filter((c) => !selectedOptionIds.has(c.option_id));
  const remainingBudget = budgetMax !== null ? budgetMax - currentCost : null;
  const isOverBudget = remainingBudget !== null && remainingBudget < 0;
  const narrativeSubheading = buildProposalNarrative(items, budgetMax, remainingBudget);

  return {
    items,
    alternatives,
    estimatedTotal: currentCost,
    remainingBudget,
    isOverBudget,
    narrativeSubheading,
  };
}

/**
 * Recalculates totals and narrative when items are swapped or removed.
 */
export function recalculateItinerary(
  items: ProposedItineraryItem[],
  allEligibleCandidates: DecisionCandidateRead[],
  budgetMax: number | null
): ProposedItinerary {
  const currentCost = items.reduce((sum, item) => sum + item.costNumber, 0);
  const selectedIds = new Set(items.map((i) => i.candidate.option_id));
  const alternatives = allEligibleCandidates.filter((c) => !selectedIds.has(c.option_id));
  const remainingBudget = budgetMax !== null ? budgetMax - currentCost : null;
  const isOverBudget = remainingBudget !== null && remainingBudget < 0;
  const narrativeSubheading = buildProposalNarrative(items, budgetMax, remainingBudget);

  return {
    items,
    alternatives,
    estimatedTotal: currentCost,
    remainingBudget,
    isOverBudget,
    narrativeSubheading,
  };
}
