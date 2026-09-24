import React, { useState, useRef } from 'react';
import { Navigation } from './components/Navigation';
import { IntentInput } from './components/IntentInput';
import type { IntentInputHandle } from './components/IntentInput';
import { LandingStory } from './components/LandingStory';
import { CapabilitiesSection } from './components/CapabilitiesSection';
import { UnderstandingCard } from './components/UnderstandingCard';
import { ProposedPlan } from './components/ProposedPlan';
import { PlanSummary } from './components/PlanSummary';
import {
  createPlanFromIntent,
  getPlan,
  getPlanRecommendations,
  addOptionToPlan,
  proposePlanAdaptation,
  applyPlanAdaptation,
} from './api/planning';
import {
  buildProposedItinerary,
  getCategoryIcon,
  buildItemSubtitle,
  parseCandidateCost,
} from './utils/itineraryBuilder';
import type { ProposedItinerary, ProposedItineraryItem } from './utils/itineraryBuilder';
import type { DecisionCandidateRead, InformationCategory, PlanRead, PlanAdaptationRead } from './types/planning';
import { IconSparkles, IconAlertCircle, IconX, IconArrowLeft, IconPlus } from './components/Icons';
import './styles.css';

export const App: React.FC = () => {
  const [currentPlan, setCurrentPlan] = useState<PlanRead | null>(null);
  const [candidates, setCandidates] = useState<DecisionCandidateRead[]>([]);
  const [proposedItinerary, setProposedItinerary] = useState<ProposedItinerary | null>(null);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [submittedIntent, setSubmittedIntent] = useState<string>('');

  const [viewMode, setViewMode] = useState<'landing' | 'workspace'>('landing');

  const [isAdaptationReview, setIsAdaptationReview] = useState(false);
  const [proposedAdaptation, setProposedAdaptation] = useState<PlanAdaptationRead | null>(null);
  const [lastTweakText, setLastTweakText] = useState('');
  const [previousItinerary, setPreviousItinerary] = useState<ProposedItinerary | null>(null);

  const [isPlanning, setIsPlanning] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isTweaking, setIsTweaking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const intentInputRef = useRef<IntentInputHandle>(null);
  const proposalRef = useRef<HTMLDivElement>(null);

  // Flow Step 1: User submits an intention
  const handleIntentSubmit = async (intent: string) => {
    setIsPlanning(true);
    setErrorMessage(null);
    setIsConfirmed(false);
    setProposedItinerary(null);
    setSubmittedIntent(intent);
    setViewMode('workspace');

    // Scroll cleanly to the workspace view
    window.scrollTo({ top: 0, behavior: 'smooth' });

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
      }, 150);
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
      setIsConfirmed(false);

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

  const handleStartNew = () => {
    setCurrentPlan(null);
    setProposedItinerary(null);
    setCandidates([]);
    setIsConfirmed(false);
    setIsAdaptationReview(false);
    setProposedAdaptation(null);
    setErrorMessage(null);
    setSubmittedIntent('');
    setViewMode('landing');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleFocusHeroInput = () => {
    if (viewMode === 'workspace') {
      setViewMode('landing');
      setTimeout(() => {
        intentInputRef.current?.focus();
      }, 100);
    } else {
      intentInputRef.current?.focus();
    }
  };

  const budgetConstraint = currentPlan?.constraints?.find((c) => c.type === 'budget_max');
  const budgetMax = budgetConstraint?.numeric_value
    ? parseFloat(String(budgetConstraint.numeric_value))
    : null;

  const hasActivePlan = Boolean(currentPlan || isPlanning);

  return (
    <div className="product-canvas">
      {/* Top Floating Navigation */}
      <Navigation
        hasActivePlan={hasActivePlan}
        isPlanning={isPlanning}
        onNewPlan={handleStartNew}
        onFocusInput={handleFocusHeroInput}
        viewMode={viewMode}
        onSwitchView={(mode) => setViewMode(mode)}
      />

      {/* Main Experience Flow */}
      <main className="product-main">
        {/* Error Notification Toast */}
        {errorMessage && (
          <div className="editorial-error-toast" role="alert">
            <div className="error-toast-content">
              <IconAlertCircle size={18} className="error-toast-icon" />
              <span>{errorMessage}</span>
            </div>
            <button
              type="button"
              className="error-toast-close"
              onClick={() => setErrorMessage(null)}
              aria-label="Dismiss error"
            >
              <IconX size={15} />
            </button>
          </div>
        )}

        {/* =========================================================================
            VIEW MODE 1: CINEMATIC LANDING EXPERIENCE
            ========================================================================= */}
        {viewMode === 'landing' && (
          <div className="landing-view-container">
            {/* Active Plan Resumption Banner (if user navigated to overview while a plan is active) */}
            {hasActivePlan && (
              <div className="active-plan-banner" onClick={() => setViewMode('workspace')}>
                <div className="active-plan-banner-text">
                  <span className="live-status-dot" />
                  <span>You have an active plan in progress: <strong>“{submittedIntent}”</strong></span>
                </div>
                <button type="button" className="active-plan-banner-btn">
                  <span>Resume plan</span>
                  <span className="banner-arrow">→</span>
                </button>
              </div>
            )}

            {/* Cinematic Hero & Command Surface */}
            <IntentInput
              ref={intentInputRef}
              onSubmit={handleIntentSubmit}
              isLoading={isPlanning}
            />

            {/* Sticky Scroll Storytelling Section (6 Chapters) */}
            <LandingStory onStartPlanning={handleFocusHeroInput} />

            {/* Engine Architecture & Capabilities Grid */}
            <CapabilitiesSection onStartPlanning={handleFocusHeroInput} />

            {/* Editorial Footer */}
            <footer className="editorial-footer">
              <div className="footer-container">
                <div className="footer-top-row">
                  <div className="footer-brand-col">
                    <span className="footer-logo">DAYFORM</span>
                    <p className="footer-tagline">
                      Intelligent real-world planning. Give shape to your day.
                    </p>
                  </div>

                  <div className="footer-links-col">
                    <span className="footer-col-title">Navigation</span>
                    <button type="button" className="footer-link" onClick={handleFocusHeroInput}>Plan an intention</button>
                    <a href="#how-it-works" className="footer-link">How it works</a>
                    <a href="#capabilities" className="footer-link">Capabilities</a>
                  </div>

                  <div className="footer-links-col">
                    <span className="footer-col-title">Engine</span>
                    <span className="footer-meta-item">Version 0.1.0</span>
                    <span className="footer-meta-item">Adaptive Sequencing</span>
                    <span className="footer-meta-item">Live Intelligence Active</span>
                  </div>
                </div>

                <div className="footer-bottom-row">
                  <span className="footer-copy">© 2026 Dayform. Built with verified places and real-world logic.</span>
                  <div className="footer-system-status">
                    <span className="live-status-dot" />
                    <span>All services operational</span>
                  </div>
                </div>
              </div>
            </footer>
          </div>
        )}

        {/* =========================================================================
            VIEW MODE 2: FOCUSED PLANNING WORKSPACE
            ========================================================================= */}
        {viewMode === 'workspace' && (
          <div className="workspace-view-container animate-fade-in">
            {/* Workspace Top Action Bar / Context Header */}
            <div className="workspace-top-bar">
              <button
                type="button"
                className="workspace-back-btn"
                onClick={() => setViewMode('landing')}
                title="Return to the overview"
              >
                <IconArrowLeft size={15} />
                <span>Overview</span>
              </button>

              <div className="workspace-intent-display">
                <span className="intent-display-badge">INTENTION</span>
                <span className="intent-display-text" title={submittedIntent}>
                  “{submittedIntent}”
                </span>
              </div>

              <button
                type="button"
                className="workspace-new-plan-btn"
                onClick={handleStartNew}
                title="Start a new plan from scratch"
              >
                <IconPlus size={14} />
                <span>New plan</span>
              </button>
            </div>

            {/* Assembling / Thinking State */}
            {isPlanning && (
              <div className="thinking-stage-container animate-fade-in">
                <div className="thinking-pulse-core">
                  <IconSparkles size={24} className="thinking-sparkle" />
                </div>
                <h3 className="thinking-title">Assembling your plan</h3>
                <p className="thinking-subtitle">
                  Evaluating local venues, live opening hours, and budget limits to curate a coherent sequence.
                </p>
                <div className="thinking-step-row">
                  <span className="thinking-step active">Parsing context</span>
                  <span className="thinking-sep">→</span>
                  <span className="thinking-step active">Checking places</span>
                  <span className="thinking-sep">→</span>
                  <span className="thinking-step active">Sequencing timeline</span>
                </div>
              </div>
            )}

            {/* Proposed Plan Stage */}
            {!isPlanning && currentPlan && proposedItinerary && !isConfirmed && (
              <div ref={proposalRef} className="proposal-stage-container animate-fade-in">
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
                  onModifyIntent={handleStartNew}
                  onTweakPlan={handleTweakPlan}
                  isTweaking={isTweaking}
                  isAdaptationReview={isAdaptationReview}
                  adaptationSummary={proposedAdaptation?.narrative_summary}
                  onAcceptAdaptation={handleAcceptAdaptation}
                  onRejectAdaptation={handleRejectAdaptation}
                />
              </div>
            )}

            {/* Confirmed / Saved Plan Stage */}
            {!isPlanning && currentPlan && isConfirmed && (
              <div className="saved-stage-container animate-fade-in">
                <PlanSummary
                  plan={currentPlan}
                  onStartNew={handleStartNew}
                  onTweakPlan={handleTweakPlan}
                  isTweaking={isTweaking}
                />
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
