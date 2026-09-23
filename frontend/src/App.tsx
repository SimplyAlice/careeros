import React, { useState, useRef } from 'react';
import { IntentInput } from './components/IntentInput';
import { UnderstandingCard } from './components/UnderstandingCard';
import { ProposedPlan } from './components/ProposedPlan';
import { PlanSummary } from './components/PlanSummary';
import { createPlanFromIntent, getPlan, getPlanRecommendations, addOptionToPlan, modifyPlan } from './api/planning';
import { buildProposedItinerary } from './utils/itineraryBuilder';
import type { ProposedItinerary } from './utils/itineraryBuilder';
import type { DecisionCandidateRead, PlanRead } from './types/planning';
import './styles.css';

export const App: React.FC = () => {
  const [currentPlan, setCurrentPlan] = useState<PlanRead | null>(null);
  const [candidates, setCandidates] = useState<DecisionCandidateRead[]>([]);
  const [proposedItinerary, setProposedItinerary] = useState<ProposedItinerary | null>(null);
  const [isConfirmed, setIsConfirmed] = useState(false);

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

  // Conversational Plan Modification ("Tweak this plan")
  const handleTweakPlan = async (tweakText: string) => {
    if (!currentPlan) return;
    setIsTweaking(true);
    setErrorMessage(null);

    try {
      // 1. Send modification delta to backend
      const updatedPlan = await modifyPlan(currentPlan.id, tweakText);
      setCurrentPlan(updatedPlan);

      // 2. Refresh recommendations with updated context & constraints
      const recsResponse = await getPlanRecommendations(updatedPlan.id);
      const allRecs = recsResponse.candidates || [];
      setCandidates(allRecs);

      // 3. Extract updated budget
      const budgetConstraint = updatedPlan.constraints?.find((c) => c.type === 'budget_max');
      const budgetMax = budgetConstraint?.numeric_value
        ? parseFloat(String(budgetConstraint.numeric_value))
        : null;

      const groupSize = updatedPlan.context?.group_size || 1;

      // 4. Re-assemble itinerary with updated understanding & candidates
      const proposal = buildProposedItinerary(
        allRecs,
        budgetMax,
        updatedPlan.intention,
        groupSize,
        updatedPlan.understanding
      );
      setProposedItinerary(proposal);
    } catch (err: unknown) {
      console.error('Error tweaking plan:', err);
      const msg = err instanceof Error ? err.message : 'Failed to update plan.';
      setErrorMessage(msg);
    } finally {
      setIsTweaking(false);
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
              key={`${currentPlan.id}-${currentPlan.updated_at || ''}-${proposedItinerary.estimatedTotal}`}
              plan={currentPlan}
              initialItinerary={proposedItinerary}
              allCandidates={candidates}
              budgetMax={budgetMax}
              onConfirm={handleConfirmPlan}
              isSaving={isSaving}
              onModifyIntent={handleModifyIntent}
              onTweakPlan={handleTweakPlan}
              isTweaking={isTweaking}
            />
          </div>
        )}

        {/* Step 3: Confirmed / Saved Plan Summary */}
        {!isPlanning && currentPlan && isConfirmed && (
          <PlanSummary
            plan={currentPlan}
            onStartNew={handleStartNew}
          />
        )}
      </main>
    </div>
  );
};

export default App;
