import React, { useState, useRef } from 'react';
import { IntentInput } from './components/IntentInput';
import { UnderstandingCard } from './components/UnderstandingCard';
import { ProposedPlan } from './components/ProposedPlan';
import { PlanSummary } from './components/PlanSummary';
import { createPlanFromIntent, getPlan, getPlanRecommendations, addOptionToPlan, proposePlanAdaptation, applyPlanAdaptation } from './api/planning';
import { buildProposedItinerary, getCategoryIcon, buildItemSubtitle, parseCandidateCost } from './utils/itineraryBuilder';
import type { ProposedItinerary, ProposedItineraryItem } from './utils/itineraryBuilder';
import type { DecisionCandidateRead, InformationCategory, PlanRead, PlanAdaptationRead } from './types/planning';
import './styles.css';

export const App: React.FC = () => {
  const [currentPlan, setCurrentPlan] = useState<PlanRead | null>(null);
  const [candidates, setCandidates] = useState<DecisionCandidateRead[]>([]);
  const [proposedItinerary, setProposedItinerary] = useState<ProposedItinerary | null>(null);
  const [isConfirmed, setIsConfirmed] = useState(false);

  const [isAdaptationReview, setIsAdaptationReview] = useState(false);
  const [proposedAdaptation, setProposedAdaptation] = useState<PlanAdaptationRead | null>(null);
  const [lastTweakText, setLastTweakText] = useState('');
  const [previousItinerary, setPreviousItinerary] = useState<ProposedItinerary | null>(null);

  const [isPlanning, setIsPlanning] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isTweaking, setIsTweaking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const inputRef = useRef<HTMLDivElement>(null);
  const proposalRef = useRef<HTMLDivElement>(null);

  // Flow Step 1: User submits an intention
  const handleIntentSubmit = async (intent: string) => {
    setIsPlanning(true);
    setErrorMessage(null);
    setIsConfirmed(false);
    setProposedItinerary(null);

    try {
      // 1. Create plan aggregate from intent (POST /api/v1/planning/requests)
      const plan = await createPlanFromIntent(intent);
      setCurrentPlan(plan);

      // 2. Fetch tailored recommendations (GET /api/v1/planning/plans/{id}/recommendations)
      const recsResponse = await getPlanRecommendations(plan.id);
      const allRecs = recsResponse.candidates || [];
      setCandidates(allRecs);

      // 3. Extract budget ceiling from constraints if present
      const budgetConstraint = plan.constraints?.find((c) => c.type === 'budget_max');
      const budgetMax = budgetConstraint?.numeric_value
        ? parseFloat(String(budgetConstraint.numeric_value))
        : null;

      const groupSize = plan.context?.group_size || 1;

      // 4. Assemble coherent proposed itinerary ("Here's what I'd do")
      const proposal = buildProposedItinerary(allRecs, budgetMax, intent, groupSize, plan.understanding);
      setProposedItinerary(proposal);

      // Smooth scroll to proposal section
      setTimeout(() => {
        proposalRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    } catch (err: unknown) {
      console.error('Planning error:', err);
      const msg = err instanceof Error ? err.message : 'Failed to create plan.';
      setErrorMessage(msg);
    } finally {
      setIsPlanning(false);
    }
  };

  // Conversational Plan Modification & Adaptive Planning ("Tweak this plan")
  const handleTweakPlan = async (tweakText: string) => {
    if (!currentPlan) return;
    setIsTweaking(true);
    setErrorMessage(null);

    try {
      // 1. Propose adaptation with minimal change and diffs
      const adaptation = await proposePlanAdaptation(currentPlan.id, tweakText);
      setProposedAdaptation(adaptation);
      setLastTweakText(tweakText);
      setPreviousItinerary(proposedItinerary);

      // 2. Fetch fresh candidates in case new category/location options are needed
      const recsResponse = await getPlanRecommendations(currentPlan.id);
      const allRecs = recsResponse.candidates || [];
      setCandidates(allRecs);

      // 3. Assemble adapted proposed itinerary from diffs
      const adaptedItems: ProposedItineraryItem[] = [];
      const removedItems: Array<{ name: string; reason: string }> = [];

      for (const diff of adaptation.diffs) {
        if (diff.action === 'removed') {
          removedItems.push({
            name: diff.original_name || 'Stop',
            reason: diff.reason,
          });
          continue;
        }

        const candidateName = diff.new_name || diff.original_name || 'Stop';
        const candidateCategory: InformationCategory = (diff.item_type === 'food' ? 'food' : 'culture');
        const matchingCand: DecisionCandidateRead = allRecs.find(
          (c) => c.option_id === diff.candidate_option_id || c.name.toLowerCase() === candidateName.toLowerCase()
        ) || {
          option_id: diff.candidate_option_id || diff.original_item_id || 'opt-' + Math.random(),
          option_type: 'place' as const,
          name: candidateName,
          is_eligible: true,
          score: 90,
          reasons: [],
          category: candidateCategory,
          cost: diff.new_cost !== undefined && diff.new_cost !== null ? String(diff.new_cost) : null,
          duration_minutes: 60,
          location: diff.location || null,
          source: 'fixture',
        };

        const itemStart = diff.new_start_time ? diff.new_start_time.substring(11, 16) : undefined;
        const itemEnd = diff.new_end_time ? diff.new_end_time.substring(11, 16) : undefined;

        adaptedItems.push({
          candidate: matchingCand,
          icon: getCategoryIcon(matchingCand.category),
          subtitle: buildItemSubtitle(matchingCand),
          costNumber: parseCandidateCost(diff.new_cost ?? matchingCand.cost),
          rationale: [diff.reason],
          startTime: itemStart,
          endTime: itemEnd,
          action: diff.action,
          changeReason: diff.reason,
          originalName: diff.original_name || undefined,
        });
      }

      const budgetConstraint = currentPlan.constraints?.find((c) => c.type === 'budget_max');
      const budgetMax = budgetConstraint?.numeric_value
        ? parseFloat(String(budgetConstraint.numeric_value))
        : null;

      const adaptedProposal: ProposedItinerary = {
        items: adaptedItems,
        alternatives: allRecs.filter((c) => !adaptedItems.some((ai) => ai.candidate.name.toLowerCase() === c.name.toLowerCase())),
        estimatedTotal: parseFloat(String(adaptation.new_total_cost || 0)),
        remainingBudget: budgetMax ? budgetMax - parseFloat(String(adaptation.new_total_cost || 0)) : null,
        isOverBudget: budgetMax ? parseFloat(String(adaptation.new_total_cost || 0)) > budgetMax : false,
        narrativeSubheading: adaptation.narrative_summary,
        adaptationSummary: adaptation.narrative_summary,
        isAdaptationProposal: true,
        removedItems,
        attribution: proposedItinerary?.attribution,
        freshness: proposedItinerary?.freshness,
      };

      setProposedItinerary(adaptedProposal);
      setIsAdaptationReview(true);
      setIsConfirmed(false); // bring user back to review proposal

      setTimeout(() => {
        proposalRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    } catch (err: unknown) {
      console.error('Error adapting plan:', err);
      const msg = err instanceof Error ? err.message : 'Failed to adapt plan.';
      setErrorMessage(msg);
    } finally {
      setIsTweaking(false);
    }
  };

  // Flow: User accepts the proposed adaptation
  const handleAcceptAdaptation = async () => {
    if (!currentPlan || !lastTweakText) return;
    setIsSaving(true);
    setErrorMessage(null);

    try {
      const updatedPlan = await applyPlanAdaptation(currentPlan.id, lastTweakText);
      setCurrentPlan(updatedPlan);
      setIsAdaptationReview(false);
      setProposedAdaptation(null);
      setIsConfirmed(true);

      setTimeout(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }, 100);
    } catch (err: unknown) {
      console.error('Error applying adaptation:', err);
      const msg = err instanceof Error ? err.message : 'Failed to apply changes.';
      setErrorMessage(msg);
    } finally {
      setIsSaving(false);
    }
  };

  // Flow: User keeps existing plan (rejects adaptation proposal)
  const handleRejectAdaptation = () => {
    if (previousItinerary) {
      setProposedItinerary(previousItinerary);
    }
    setIsAdaptationReview(false);
    setProposedAdaptation(null);
    if (currentPlan && currentPlan.items.length > 0) {
      setIsConfirmed(true);
    }
  };

  // Flow Step 2: User confirms the proposed itinerary ("Looks good")
  const handleConfirmPlan = async (selectedCandidates: DecisionCandidateRead[]) => {
    if (!currentPlan) return;

    setIsSaving(true);
    setErrorMessage(null);

    try {
      // Persist each selected candidate to the authoritative backend plan
      for (const candidate of selectedCandidates) {
        await addOptionToPlan(currentPlan.id, candidate);
      }

      // Refresh plan from database (GET /api/v1/planning/plans/{plan_id})
      const refreshed = await getPlan(currentPlan.id);
      setCurrentPlan(refreshed);
      setIsConfirmed(true);

      // Smooth scroll to confirmed plan
      setTimeout(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }, 100);
    } catch (err: unknown) {
      console.error('Error confirming plan:', err);
      const msg = err instanceof Error ? err.message : 'Failed to save plan.';
      setErrorMessage(msg);
    } finally {
      setIsSaving(false);
    }
  };

  // User wants to modify request or start over
  const handleModifyIntent = () => {
    inputRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleStartNew = () => {
    setCurrentPlan(null);
    setProposedItinerary(null);
    setCandidates([]);
    setIsConfirmed(false);
    setIsAdaptationReview(false);
    setProposedAdaptation(null);
    setErrorMessage(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const budgetConstraint = currentPlan?.constraints?.find((c) => c.type === 'budget_max');
  const budgetMax = budgetConstraint?.numeric_value
    ? parseFloat(String(budgetConstraint.numeric_value))
    : null;

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-inner">
          <div className="brand-logo" onClick={handleStartNew} style={{ cursor: 'pointer' }}>
            <h1 className="brand-name">OpsOS</h1>
            <span className="brand-tagline">Intelligent Real-World Planning</span>
          </div>
          <div className="header-status">
            <span className="status-dot" />
            <span>Ready to Plan</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="app-main">
        {/* Error notification */}
        {errorMessage && (
          <div className="error-banner">
            <span>{errorMessage}</span>
            <button
              type="button"
              className="error-close"
              onClick={() => setErrorMessage(null)}
            >
              ✕
            </button>
          </div>
        )}

        {/* Step 1: Homepage Hero & Natural Language Input */}
        <div ref={inputRef}>
          <IntentInput
            onSubmit={handleIntentSubmit}
            isLoading={isPlanning}
          />
        </div>

        {/* Planning Loading State */}
        {isPlanning && (
          <div className="planning-loading-card">
            <div className="spinner large" />
            <h3 className="planning-loading-title">Figuring out your plan...</h3>
            <p className="planning-loading-subtitle">
              Analyzing constraints, group size, and local options to assemble a great sequence.
            </p>
          </div>
        )}

        {/* Step 2: Understanding Card & Proposed Plan */}
        {!isPlanning && currentPlan && proposedItinerary && !isConfirmed && (
          <div ref={proposalRef} className="proposal-section-wrapper">
            <UnderstandingCard
              plan={currentPlan}
              budgetMax={budgetMax}
            />

            <ProposedPlan
              key={`${currentPlan.id}-${currentPlan.updated_at || ''}-${proposedItinerary.estimatedTotal}-${isAdaptationReview ? 'review' : 'normal'}`}
              plan={currentPlan}
              initialItinerary={proposedItinerary}
              allCandidates={candidates}
              budgetMax={budgetMax}
              onConfirm={handleConfirmPlan}
              isSaving={isSaving}
              onModifyIntent={handleModifyIntent}
              onTweakPlan={handleTweakPlan}
              isTweaking={isTweaking}
              isAdaptationReview={isAdaptationReview}
              adaptationSummary={proposedAdaptation?.narrative_summary}
              onAcceptAdaptation={handleAcceptAdaptation}
              onRejectAdaptation={handleRejectAdaptation}
            />
          </div>
        )}

        {/* Step 3: Confirmed / Saved Plan Summary */}
        {!isPlanning && currentPlan && isConfirmed && (
          <PlanSummary
            plan={currentPlan}
            onStartNew={handleStartNew}
            onTweakPlan={handleTweakPlan}
            isTweaking={isTweaking}
          />
        )}
      </main>
    </div>
  );
};

export default App;
