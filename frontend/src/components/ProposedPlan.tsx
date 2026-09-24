import React, { useState, useEffect } from 'react';
import type { DecisionCandidateRead, PlanRead } from '../types/planning';
import type { ProposedItineraryItem, ProposedItinerary } from '../utils/itineraryBuilder';
import {
  formatCurrency,
  parseCandidateCost,
  recalculateItinerary,
  humanizeCandidateReasons,
  getTradeOffNote,
} from '../utils/itineraryBuilder';
import {
  CategoryIcon,
  IconArrowRight,
  IconClock,
  IconMapPin,
  IconSwap,
  IconTrash,
  IconPlus,
  IconCheck,
  IconSparkles,
  IconAlertCircle,
  IconX,
} from './Icons';

interface ProposedPlanProps {
  plan: PlanRead;
  initialItinerary: ProposedItinerary;
  allCandidates: DecisionCandidateRead[];
  budgetMax: number | null;
  onConfirm: (selectedCandidates: DecisionCandidateRead[]) => Promise<void>;
  isSaving: boolean;
  onModifyIntent: () => void;
  onTweakPlan?: (tweakText: string) => Promise<void>;
  isTweaking?: boolean;
  isAdaptationReview?: boolean;
  adaptationSummary?: string;
  onAcceptAdaptation?: () => Promise<void>;
  onRejectAdaptation?: () => void;
}

export const ProposedPlan: React.FC<ProposedPlanProps> = ({
  plan,
  initialItinerary,
  allCandidates,
  budgetMax,
  onConfirm,
  isSaving,
  onModifyIntent,
  onTweakPlan,
  isTweaking = false,
  isAdaptationReview = false,
  adaptationSummary,
  onAcceptAdaptation,
  onRejectAdaptation,
}) => {
  const [itinerary, setItinerary] = useState<ProposedItinerary>(initialItinerary);
  const [swappingIndex, setSwappingIndex] = useState<number | null>(null);
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [customTweak, setCustomTweak] = useState('');

  useEffect(() => {
    setItinerary(initialItinerary);
  }, [initialItinerary]);

  const groupSize = plan.context?.group_size || 1;

  // Swap an item in slot index with an alternative candidate
  const handleSwap = (slotIndex: number, newCandidate: DecisionCandidateRead) => {
    const updatedItems = [...itinerary.items];
    updatedItems[slotIndex] = {
      candidate: newCandidate,
      icon: newCandidate.category,
      subtitle: newCandidate.address || newCandidate.location || '',
      costNumber: parseCandidateCost(newCandidate.cost),
      rationale: humanizeCandidateReasons(newCandidate, budgetMax, groupSize, plan.understanding),
    };

    const recalculated = recalculateItinerary(updatedItems, allCandidates, budgetMax, plan.understanding);
    setItinerary(recalculated);
    setSwappingIndex(null);
  };

  // Remove an item from the proposed itinerary
  const handleRemove = (slotIndex: number) => {
    const updatedItems = itinerary.items.filter((_, idx) => idx !== slotIndex);
    const recalculated = recalculateItinerary(updatedItems, allCandidates, budgetMax, plan.understanding);
    setItinerary(recalculated);
    if (swappingIndex === slotIndex) {
      setSwappingIndex(null);
    }
  };

  // Add an alternative candidate to the itinerary
  const handleAdd = (candidate: DecisionCandidateRead) => {
    const newItem: ProposedItineraryItem = {
      candidate,
      icon: candidate.category,
      subtitle: candidate.address || candidate.location || '',
      costNumber: parseCandidateCost(candidate.cost),
      rationale: humanizeCandidateReasons(candidate, budgetMax, groupSize, plan.understanding),
    };
    const updatedItems = [...itinerary.items, newItem];
    const recalculated = recalculateItinerary(updatedItems, allCandidates, budgetMax, plan.understanding);
    setItinerary(recalculated);
    setShowAddMenu(false);
  };

  const handleConfirmClick = async () => {
    const candidatesToPersist = itinerary.items.map((i) => i.candidate);
    await onConfirm(candidatesToPersist);
  };

  // Budget calculations for clean summary
  const totalCost = itinerary.estimatedTotal;
  const budgetBudgeted = budgetMax !== null;
  const remaining = itinerary.remainingBudget;
  const progressPercent = budgetBudgeted && budgetMax > 0 ? Math.min(100, Math.round((totalCost / budgetMax) * 100)) : 100;

  return (
    <div className="proposed-itinerary-container">
      {/* Adaptation Review Notice */}
      {(isAdaptationReview || itinerary.isAdaptationProposal) && (
        <div className="adaptation-review-banner">
          <div className="adaptation-banner-header">
            <div className="adaptation-banner-tag">
              <IconSparkles size={14} />
              <span>PLAN ADAPTATION PROPOSED</span>
            </div>
            <span className="adaptation-minimal-tag">Minimal Change Preserved</span>
          </div>
          <p className="adaptation-banner-summary">
            {adaptationSummary || itinerary.adaptationSummary || 'Adapted itinerary according to your requested change.'}
          </p>
        </div>
      )}

      {/* Editorial Header */}
      <div className="itinerary-editorial-header">
        <div className="itinerary-header-top">
          <div className="itinerary-eyebrow">
            <span className="eyebrow-dot" />
            <span>PROPOSED SEQUENCE</span>
            {plan.understanding?.date_spec && (
              <>
                <span className="eyebrow-sep">·</span>
                <span>{plan.understanding.date_spec}</span>
              </>
            )}
            {itinerary.timeSpanDisplay && (
              <>
                <span className="eyebrow-sep">·</span>
                <span>{itinerary.timeSpanDisplay}</span>
              </>
            )}
          </div>

          <div className="itinerary-freshness-indicator">
            <span className="freshness-dot live" />
            <span className="freshness-text">Verified real-world places</span>
          </div>
        </div>

        <h2 className="itinerary-main-title">Here’s what I’d do.</h2>
        <p className="itinerary-narrative-subheading">{itinerary.narrativeSubheading}</p>
      </div>

      {/* Refined Budget Bar */}
      <div className="editorial-budget-bar">
        <div className="budget-bar-labels">
          <div className="budget-primary-stat">
            <span className="budget-stat-label">Estimated total:</span>
            <span className="budget-stat-value">{formatCurrency(totalCost)}</span>
          </div>
          {budgetBudgeted && (
            <div className="budget-secondary-stat">
              <span className="budget-stat-label">
                {itinerary.isOverBudget ? 'Over budget by' : 'Remaining budget:'}
              </span>
              <span className={`budget-stat-value ${itinerary.isOverBudget ? 'alert' : 'positive'}`}>
                {remaining !== null && remaining >= 0
                  ? `${formatCurrency(remaining)} left to spare`
                  : `${formatCurrency(Math.abs(remaining || 0))}`}
              </span>
            </div>
          )}
        </div>

        {budgetBudgeted && (
          <div className="budget-meter-track">
            <div
              className={`budget-meter-fill ${itinerary.isOverBudget ? 'over' : ''}`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        )}
      </div>

      {/* Editorial Timeline */}
      <div className="editorial-timeline">
        {itinerary.items.length === 0 ? (
          <div className="empty-timeline-state">
            <p className="empty-timeline-text">All stops have been removed from this plan.</p>
            {itinerary.alternatives.length > 0 && (
              <button
                type="button"
                className="btn-editorial-text"
                onClick={() => setShowAddMenu(true)}
              >
                <IconPlus size={14} />
                <span>Add a place to your plan</span>
              </button>
            )}
          </div>
        ) : (
          itinerary.items.map((item, idx) => {
            const isSwapping = swappingIndex === idx;
            const isLast = idx === itinerary.items.length - 1;
            const categoryName = item.candidate.category.toUpperCase();

            return (
              <div key={item.candidate.option_id} className={`timeline-node ${isLast ? 'last' : ''}`}>
                {/* Vertical Spine & Time Anchor */}
                <div className="timeline-spine">
                  <div className="timeline-marker">
                    <CategoryIcon category={item.candidate.category} size={14} className="timeline-category-icon" />
                  </div>
                  {!isLast && <div className="timeline-line" />}
                </div>

                {/* Timeline Content Block */}
                <div className="timeline-content-card">
                  {/* Top Meta Line: Time + Category + Cost */}
                  <div className="timeline-meta-row">
                    <div className="timeline-time-group">
                      {item.startTime && item.endTime ? (
                        <div className="timeline-time-badge">
                          <IconClock size={13} className="time-icon" />
                          <span>{item.startTime} – {item.endTime}</span>
                          {item.durationMinutes && <span className="time-duration">({item.durationMinutes}m)</span>}
                        </div>
                      ) : (
                        <div className="timeline-time-badge subtle">
                          <IconClock size={13} className="time-icon" />
                          <span>Flexible time</span>
                        </div>
                      )}

                      <span className="timeline-category-tag">{categoryName}</span>

                      {item.action === 'rescheduled' && (
                        <span className="timeline-action-badge rescheduled">Rescheduled</span>
                      )}
                      {item.action === 'replaced' && (
                        <span className="timeline-action-badge replaced">
                          Replaced {item.originalName ? `(${item.originalName})` : ''}
                        </span>
                      )}
                      {item.action === 'kept' && (
                        <span className="timeline-action-badge kept">Kept</span>
                      )}
                    </div>

                    <div className="timeline-price-tag">
                      {formatCurrency(item.costNumber)}
                    </div>
                  </div>

                  {/* Title & Location */}
                  <div className="timeline-title-area">
                    <h3 className="timeline-venue-name">{item.candidate.name}</h3>
                    {(item.candidate.address || item.candidate.location) && (
                      <div className="timeline-venue-address">
                        <IconMapPin size={13} className="address-pin" />
                        <span>{item.candidate.address || item.candidate.location}</span>
                      </div>
                    )}
                  </div>

                  {/* Opening hours badge if verified */}
                  {item.candidate.opening_hours && (
                    <div className="timeline-hours-pill">
                      <IconClock size={12} />
                      <span>{item.candidate.opening_hours}</span>
                    </div>
                  )}

                  {/* Why this stop fits (Human planner rationale) */}
                  {item.rationale && item.rationale.length > 0 && (
                    <div className="timeline-rationale-box">
                      <div className="rationale-accent-line" />
                      <div className="rationale-text-content">
                        {item.rationale.map((reason, rIdx) => (
                          <div key={rIdx} className="rationale-line">
                            {reason}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Secondary Contextual Controls (Swap / Remove) */}
                  <div className="timeline-controls-row">
                    {itinerary.alternatives.length > 0 && (
                      <button
                        type="button"
                        className={`timeline-action-btn ${isSwapping ? 'active' : ''}`}
                        onClick={() => setSwappingIndex(isSwapping ? null : idx)}
                        disabled={isSaving}
                      >
                        <IconSwap size={13} />
                        <span>{isSwapping ? 'Close alternatives' : 'Swap option'}</span>
                      </button>
                    )}

                    <button
                      type="button"
                      className="timeline-action-btn delete"
                      onClick={() => handleRemove(idx)}
                      disabled={isSaving}
                    >
                      <IconTrash size={13} />
                      <span>Remove</span>
                    </button>
                  </div>

                  {/* Inline Swap Alternative Drawer */}
                  {isSwapping && (
                    <div className="timeline-swap-drawer">
                      <div className="swap-drawer-header">
                        <span>Select an alternative for this stop:</span>
                        <button
                          type="button"
                          className="btn-drawer-close"
                          onClick={() => setSwappingIndex(null)}
                        >
                          <IconX size={14} />
                        </button>
                      </div>

                      <div className="swap-drawer-options">
                        {itinerary.alternatives.map((alt) => {
                          const tradeOff = getTradeOffNote(alt, item.candidate);
                          return (
                            <div key={alt.option_id} className="swap-drawer-item">
                              <div className="swap-item-primary">
                                <div className="swap-item-title-row">
                                  <span className="swap-item-name">{alt.name}</span>
                                  <span className="swap-tradeoff-tag">{tradeOff}</span>
                                </div>
                                <div className="swap-item-meta">
                                  <span>{alt.category}</span>
                                  <span className="meta-sep">·</span>
                                  <span>{formatCurrency(alt.cost)}</span>
                                  {alt.duration_minutes && (
                                    <>
                                      <span className="meta-sep">·</span>
                                      <span>{alt.duration_minutes}m</span>
                                    </>
                                  )}
                                  {alt.location && (
                                    <>
                                      <span className="meta-sep">·</span>
                                      <span>{alt.location}</span>
                                    </>
                                  )}
                                </div>
                              </div>

                              <button
                                type="button"
                                className="btn-select-swap"
                                onClick={() => handleSwap(idx, alt)}
                              >
                                Replace with this
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Add Another Stop Trigger */}
      {itinerary.items.length > 0 && itinerary.items.length < 4 && itinerary.alternatives.length > 0 && !showAddMenu && (
        <div className="add-stop-container">
          <button
            type="button"
            className="btn-add-stop"
            onClick={() => setShowAddMenu(true)}
            disabled={isSaving}
          >
            <IconPlus size={15} />
            <span>Add another stop to your plan</span>
          </button>
        </div>
      )}

      {/* Add Drawer */}
      {showAddMenu && itinerary.alternatives.length > 0 && (
        <div className="add-options-panel">
          <div className="swap-drawer-header">
            <span>Available places to add:</span>
            <button
              type="button"
              className="btn-drawer-close"
              onClick={() => setShowAddMenu(false)}
            >
              <IconX size={14} />
            </button>
          </div>

          <div className="swap-drawer-options">
            {itinerary.alternatives.map((alt) => (
              <div key={alt.option_id} className="swap-drawer-item">
                <div className="swap-item-primary">
                  <div className="swap-item-title-row">
                    <span className="swap-item-name">{alt.name}</span>
                  </div>
                  <div className="swap-item-meta">
                    <span>{alt.category}</span>
                    <span className="meta-sep">·</span>
                    <span>{formatCurrency(alt.cost)}</span>
                    {alt.location && (
                      <>
                        <span className="meta-sep">·</span>
                        <span>{alt.location}</span>
                      </>
                    )}
                  </div>
                </div>

                <button
                  type="button"
                  className="btn-select-swap"
                  onClick={() => handleAdd(alt)}
                >
                  Add to plan
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Conversational Tweak ("Something changed?") */}
      {onTweakPlan && (
        <div className="conversational-adaptation-panel">
          <div className="tweak-panel-header">
            <h4 className="tweak-panel-title">Something changed?</h4>
            <p className="tweak-panel-subtitle">
              Tell me what happened and I’ll rework the plan while keeping your context.
            </p>
          </div>

          {/* Quick Adjustment Chips */}
          <div className="tweak-quick-chips">
            {['Make it cheaper', 'Sheltered / indoor only', 'Add 2 people', 'Make it Sunday'].map(
              (chip) => (
                <button
                  key={chip}
                  type="button"
                  className="tweak-chip-button"
                  disabled={isTweaking || isSaving}
                  onClick={() => onTweakPlan(chip)}
                >
                  + {chip}
                </button>
              )
            )}
          </div>

          {/* Integrated Tweak Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (customTweak.trim() && !isTweaking && !isSaving) {
                onTweakPlan(customTweak.trim());
                setCustomTweak('');
              }
            }}
            className="tweak-input-form"
          >
            <input
              type="text"
              value={customTweak}
              onChange={(e) => setCustomTweak(e.target.value)}
              placeholder="e.g. Kloof Street House is fully booked, or keep it under R800..."
              disabled={isTweaking || isSaving}
              className="tweak-text-input"
            />
            <button
              type="submit"
              disabled={!customTweak.trim() || isTweaking || isSaving}
              className="tweak-submit-button"
            >
              {isTweaking ? (
                <span className="tweak-loading">
                  <span className="loading-spinner small" />
                  <span>Reworking...</span>
                </span>
              ) : (
                'Adapt plan'
              )}
            </button>
          </form>
        </div>
      )}

      {/* Removed Items Section if Adaptation Removed Stops */}
      {itinerary.removedItems && itinerary.removedItems.length > 0 && (
        <div className="adaptation-removed-stops">
          <div className="removed-stops-header">
            <IconAlertCircle size={14} className="removed-icon" />
            <span>Removed Stops (cannot fit revised constraints):</span>
          </div>
          <ul className="removed-stops-list">
            {itinerary.removedItems.map((rem, rIdx) => (
              <li key={rIdx}>
                <strong>{rem.name}</strong> — {rem.reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Bottom Primary Confirm / Actions */}
      <div className="itinerary-bottom-actions">
        {isAdaptationReview ? (
          <div className="adaptation-review-actions">
            <button
              type="button"
              className="btn-editorial-primary"
              onClick={onAcceptAdaptation}
              disabled={isSaving || isTweaking}
            >
              {isSaving ? (
                <span className="btn-loading-wrap">
                  <span className="loading-spinner" />
                  <span>Applying changes...</span>
                </span>
              ) : (
                <span className="btn-label-wrap">
                  <span>Accept changes</span>
                  <IconCheck size={16} />
                </span>
              )}
            </button>

            <button
              type="button"
              className="btn-editorial-secondary"
              onClick={onRejectAdaptation}
              disabled={isSaving || isTweaking}
            >
              Keep existing plan
            </button>
          </div>
        ) : (
          <div className="normal-confirm-actions">
            <button
              type="button"
              className="btn-editorial-primary large"
              onClick={handleConfirmClick}
              disabled={isSaving || isTweaking || itinerary.items.length === 0}
            >
              {isSaving ? (
                <span className="btn-loading-wrap">
                  <span className="loading-spinner" />
                  <span>Saving your plan...</span>
                </span>
              ) : (
                <span className="btn-label-wrap">
                  <span>Looks good</span>
                  <IconArrowRight size={17} />
                </span>
              )}
            </button>

            <button
              type="button"
              className="btn-editorial-ghost"
              onClick={onModifyIntent}
              disabled={isSaving}
            >
              Try a different request
            </button>
          </div>
        )}
      </div>

      {itinerary.attribution && (
        <div className="itinerary-attribution-footer">
          Place and map information {itinerary.attribution}
        </div>
      )}
    </div>
  );
};
