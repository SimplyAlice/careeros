import React, { useState } from 'react';
import { IntentInput } from './components/IntentInput';
import { PlanSummary } from './components/PlanSummary';
import { RecommendationCard } from './components/RecommendationCard';
import { createPlanFromIntent, getPlan, getPlanRecommendations, addOptionToPlan } from './api/planning';
import type { DecisionCandidateRead, PlanRead } from './types/planning';
import './styles.css';

export const App: React.FC = () => {
  const [currentPlan, setCurrentPlan] = useState<PlanRead | null>(null);
  const [recommendations, setRecommendations] = useState<DecisionCandidateRead[]>([]);
  const [addedOptionIds, setAddedOptionIds] = useState<Set<string>>(new Set());

  const [isPlanning, setIsPlanning] = useState(false);
  const [isLoadingRecs, setIsLoadingRecs] = useState(false);
  const [addingOptionId, setAddingOptionId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Flow Step 1: User submits an intention
  const handleIntentSubmit = async (intent: string) => {
    setIsPlanning(true);
    setErrorMessage(null);
    setAddedOptionIds(new Set());

    try {
      // 1. Create plan from intent (POST /api/v1/planning/requests)
      const plan = await createPlanFromIntent(intent);
      setCurrentPlan(plan);

      // 2. Fetch recommendations (GET /api/v1/planning/plans/{id}/recommendations)
      setIsLoadingRecs(true);
      try {
        const recsResponse = await getPlanRecommendations(plan.id);
        setRecommendations(recsResponse.candidates || []);
      } catch (recErr) {
        console.error('Failed to load recommendations:', recErr);
        const msg = recErr instanceof Error ? recErr.message : 'Failed to load option recommendations.';
        setErrorMessage(msg);
      } finally {
        setIsLoadingRecs(false);
      }
    } catch (err: unknown) {
      console.error('Planning error:', err);
      const msg = err instanceof Error ? err.message : 'Failed to create plan.';
      setErrorMessage(msg);
    } finally {
      setIsPlanning(false);
    }
  };

  // Flow Step 4: User selects a recommendation card
  const handleSelectOption = async (candidate: DecisionCandidateRead) => {
    if (!currentPlan) return;

    setAddingOptionId(candidate.option_id);
    setErrorMessage(null);

    try {
      // 1. Post selection to authoritative endpoint
      // POST /api/v1/planning/plans/{plan_id}/items/from-option
      await addOptionToPlan(currentPlan.id, candidate);

      // Mark as added in UI
      setAddedOptionIds((prev) => new Set(prev).add(candidate.option_id));

      // 2. Refresh plan directly from server (GET /api/v1/planning/plans/{plan_id})
      const refreshed = await getPlan(currentPlan.id);
      setCurrentPlan(refreshed);
    } catch (err: unknown) {
      console.error('Error adding item to plan:', err);
      const msg = err instanceof Error ? err.message : 'Failed to add item to plan.';
      setErrorMessage(msg);
    } finally {
      setAddingOptionId(null);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-inner">
          <div className="brand-logo">
            <h1 className="brand-name">OpsOS</h1>
            <span className="brand-tagline">Personal Real-World Planner</span>
          </div>
          <div className="header-status">
            <span className="status-dot" />
            <span>Backend Connected</span>
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

        {/* Step 1: Intent Input */}
        <IntentInput
          onSubmit={handleIntentSubmit}
          isLoading={isPlanning}
        />

        {/* Step 2: Plan Overview & Selected Items */}
        {currentPlan && (
          <PlanSummary plan={currentPlan} />
        )}

        {/* Step 3: Recommendations Grid */}
        {currentPlan && (
          <section className="recommendations-section">
            <div className="section-header">
              <h3 className="section-title">Recommended for your plan</h3>
              <p className="section-subtitle">
                Tailored options scored against your location, group size, and budget with explainable reasons.
              </p>
            </div>

            {isLoadingRecs ? (
              <div className="loading-block">
                <div className="spinner" />
                <p>Curating the best options for your group...</p>
              </div>
            ) : recommendations.length === 0 ? (
              <div className="empty-block">
                <p>No recommendations found matching your exact criteria. Try adjusting your constraints.</p>
              </div>
            ) : (
              <div className="recommendations-grid">
                {recommendations.map((candidate) => (
                  <RecommendationCard
                    key={candidate.option_id}
                    candidate={candidate}
                    onSelect={handleSelectOption}
                    isAdding={addingOptionId === candidate.option_id}
                    isAdded={
                      addedOptionIds.has(candidate.option_id) ||
                      Boolean(currentPlan.items.some((i) => i.name === candidate.name))
                    }
                  />
                ))}
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
};

export default App;
