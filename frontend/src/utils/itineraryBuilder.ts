import type { DecisionCandidateRead, InformationCategory, UnderstandingRead } from '../types/planning';

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
  groupSize: number = 1,
  understanding?: UnderstandingRead | null
): string[] {
  const humanReasons: string[] = [];
  const cost = parseCandidateCost(candidate.cost);

  // 1. Budget rationale
  if (cost === 0) {
    humanReasons.push('Free to enjoy — zero impact on your budget.');
  } else if (budgetMax !== null && cost <= budgetMax) {
    humanReasons.push(`Fits comfortably within your ${formatCurrency(budgetMax)} budget.`);
  }

  // 2. Occasion rationale
  if (understanding?.occasion === 'date') {
    humanReasons.push('A great, relaxed setting for a date.');
  } else if (understanding?.occasion === 'birthday') {
    humanReasons.push('A celebratory spot for a special day.');
  } else if (understanding?.occasion === 'friends') {
    humanReasons.push('Fun, easygoing setting for a group of friends.');
  }

  // 3. Group suitability
  if (groupSize > 1) {
    humanReasons.push(`Well suited for a group of ${groupSize}.`);
  }

  // 4. Category context
  if (candidate.category === 'nature') {
    humanReasons.push('Offers a scenic, relaxed outdoor start.');
  } else if (candidate.category === 'culture') {
    humanReasons.push('Adds a rich cultural dimension to your plan.');
  } else if (candidate.category === 'food') {
    humanReasons.push('Great spot for group conversation and food.');
  }

  // Fallback to any positive message from backend reasons if human list is small
  if (candidate.reasons) {
    for (const r of candidate.reasons) {
      if (r.outcome === 'supported' && r.message) {
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
  remainingBudget: number | null,
  understanding?: UnderstandingRead | null
): string {
  const categories = new Set(items.map((i) => i.candidate.category));

  if (understanding?.occasion === 'date') {
    if (remainingBudget !== null && remainingBudget > 0) {
      return `A romantic outing designed for the two of you, with ${formatCurrency(remainingBudget)} left to spare.`;
    }
    return 'A relaxed, memorable date outing tailored for the two of you.';
  }

  if (understanding?.occasion === 'birthday') {
    const forWho = understanding.relationship_context ? ` for your ${understanding.relationship_context}` : '';
    if (remainingBudget !== null && remainingBudget > 0) {
      return `A celebratory birthday plan${forWho}, with ${formatCurrency(remainingBudget)} left to spare.`;
    }
    return `A thoughtful birthday celebration${forWho} tailored to what you asked for.`;
  }

  if (understanding?.occasion === 'friends') {
    const countStr = understanding.people_count ? `the ${understanding.people_count} of you` : 'your group';
    if (remainingBudget !== null && remainingBudget > 0) {
      return `A fun outing for ${countStr}, with ${formatCurrency(remainingBudget)} left in your budget.`;
    }
    return `A fun group plan tailored for ${countStr}.`;
  }

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
 * Understanding-aware and constraint-respecting:
 * - Strictly filters out candidates violating exclusions (e.g. no outdoor, not fancy).
 * - Prioritizes requested themes (food, outdoors, culture, date) when present.
 * - Otherwise builds a varied, non-repetitive sequence across categories.
 * - Strictly enforces budget limits.
 */
export function buildProposedItinerary(
  candidates: DecisionCandidateRead[],
  budgetMax: number | null,
  _intentText: string = '',
  groupSize: number = 1,
  understanding?: UnderstandingRead | null
): ProposedItinerary {
  let eligible = candidates.filter((c) => c.is_eligible);

  // Client-side safety filter against exclusions
  if (understanding?.exclusions && understanding.exclusions.length > 0) {
    if (understanding.exclusions.includes('no_outdoors')) {
      eligible = eligible.filter((c) => c.category !== 'nature');
    }
    if (understanding.exclusions.includes('not_too_fancy')) {
      eligible = eligible.filter((c) => {
        const cost = parseCandidateCost(c.cost);
        const nameLower = c.name.toLowerCase();
        return cost < 400 && !nameLower.includes('fine dining') && !nameLower.includes('luxury');
      });
    }
  }

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

  const selectedCandidates: DecisionCandidateRead[] = [];
  const selectedOptionIds = new Set<string>();
  const selectedCategories = new Set<string>();
  let currentCost = 0;

  // 1. If user has a strong focus or activity_type preference, pick top candidate from that category first
  const preferredCats = understanding?.activity_types || [];
  if (preferredCats.length > 0) {
    for (const cat of preferredCats) {
      const match = eligible.find((c) => c.category === cat && !selectedOptionIds.has(c.option_id));
      if (match) {
        const cost = parseCandidateCost(match.cost);
        if (budgetMax === null || currentCost + cost <= budgetMax) {
          selectedCandidates.push(match);
          selectedOptionIds.add(match.option_id);
          selectedCategories.add(match.category);
          currentCost += cost;
          break;
        }
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
    rationale: humanizeCandidateReasons(candidate, budgetMax, groupSize, understanding),
  }));

  const alternatives = eligible.filter((c) => !selectedOptionIds.has(c.option_id));
  const remainingBudget = budgetMax !== null ? budgetMax - currentCost : null;
  const isOverBudget = remainingBudget !== null && remainingBudget < 0;
  const narrativeSubheading = buildProposalNarrative(items, budgetMax, remainingBudget, understanding);

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
