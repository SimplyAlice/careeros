import React, { useState } from 'react';
import type { DecisionCandidateRead, PlanRead } from '../types/planning';
import type { ProposedItineraryItem, ProposedItinerary } from '../utils/itineraryBuilder';
import {
  formatCurrency,
  getCategoryIcon,
  buildItemSubtitle,
  parseCandidateCost,
  recalculateItinerary,
  humanizeCandidateReasons,
  getTradeOffNote,
} from '../utils/itineraryBuilder';

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
}) => {
  const [itinerary, setItinerary] = useState<ProposedItinerary>(initialItinerary);
  const [swappingIndex, setSwappingIndex] = useState<number | null>(null);
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [customTweak, setCustomTweak] = useState('');

  const groupSize = plan.context?.group_size || 1;

  // Swap an item in slot index with an alternative candidate
  const handleSwap = (slotIndex: number, newCandidate: DecisionCandidateRead) => {
    const updatedItems = [...itinerary.items];
    updatedItems[slotIndex] = {
      candidate: newCandidate,
      icon: getCategoryIcon(newCandidate.category),
      subtitle: buildItemSubtitle(newCandidate),
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
      icon: getCategoryIcon(candidate.category),
      subtitle: buildItemSubtitle(candidate),
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

  return (
    <div className="proposed-plan-card">
      {/* Editorial Header */}
      <div className="proposal-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="proposal-badge">Proposed Itinerary</span>
            {plan.understanding?.date_spec && (
              <span style={{ fontSize: '0.8125rem', color: '#6366f1', fontWeight: 600, background: '#eef2ff', padding: '2px 8px', borderRadius: '4px' }}>
                📅 {plan.understanding.date_spec}
                {itinerary.timeSpanDisplay ? ` · ${itinerary.timeSpanDisplay}` : ''}
              </span>
            )}
          </div>
          {itinerary.freshness === 'live' ? (
            <span style={{ fontSize: '0.75rem', color: '#16a34a', fontWeight: 500 }}>
              ● Live information
            </span>
          ) : itinerary.freshness === 'recently_verified' ? (
            <span style={{ fontSize: '0.75rem', color: '#4b5563', fontWeight: 500 }}>
              ✓ Verified real-world places
            </span>
          ) : null}
        </div>
        <h2 className="proposal-title">Here’s what I’d do</h2>
        <p className="proposal-subtitle">{itinerary.narrativeSubheading}</p>
      </div>

      {/* Sequential Itinerary Timeline */}
      <div className="proposal-timeline">
        {itinerary.items.length === 0 ? (
          <div className="empty-proposal">
            <p className="empty-proposal-text">All stops have been removed from this plan.</p>
            {itinerary.alternatives.length > 0 && (
              <button
                type="button"
                className="btn-link-action"
                onClick={() => setShowAddMenu(true)}
              >
                + Add an option back to your plan
              </button>
            )}
          </div>
        ) : (
          itinerary.items.map((item, idx) => {
            const isSwapping = swappingIndex === idx;
            const stepNumber = String(idx + 1).padStart(2, '0');

            return (
              <div key={item.candidate.option_id} className="timeline-step">
                <div className="step-indicator">
                  <div className="step-circle">{stepNumber}</div>
                  {item.startTime && (
                    <div style={{ fontSize: '0.72rem', fontWeight: 600, color: '#4f46e5', marginTop: '4px', textAlign: 'center' }}>
                      {item.startTime}
                    </div>
                  )}
                  {idx < itinerary.items.length - 1 && <div className="step-line" />}
                </div>

                <div className="step-card">
                  <div className="step-main">
                    <div className="step-header">
                      <div className="step-title-area">
                        <span className="step-icon">{item.icon}</span>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                            <h3 className="step-name" style={{ margin: 0 }}>{item.candidate.name}</h3>
                            {item.startTime && item.endTime && (
                              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#4338ca', background: '#eef2ff', padding: '1px 6px', borderRadius: '4px', border: '1px solid #c7d2fe' }}>
                                ⏱️ {item.startTime} – {item.endTime} ({item.durationMinutes}m)
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="step-cost-area">
                        <span className="step-cost">
                          {formatCurrency(item.costNumber)}
                        </span>
                      </div>
                    </div>

                    <div className="step-subtitle">{item.subtitle}</div>


                    {item.candidate.opening_hours && (
                      <div style={{ fontSize: '0.75rem', color: '#52525b', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <span>🕐</span>
                        <span>{item.candidate.opening_hours}</span>
                      </div>
                    )}

                    {/* Decision Explanation: Human language rationale */}
                    {item.rationale && item.rationale.length > 0 && (
                      <div className="step-rationale-box">
                        <span className="rationale-header">Why I chose this</span>
                        <ul className="rationale-list">
                          {item.rationale.map((reason, rIdx) => (
                            <li key={rIdx} className="rationale-item">
                              <span className="bullet">✓</span>
                              <span>{reason}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Step Action buttons */}
                  <div className="step-actions">
                    {itinerary.alternatives.length > 0 && (
                      <button
                        type="button"
                        className="btn-text-action swap"
                        onClick={() => setSwappingIndex(isSwapping ? null : idx)}
                        disabled={isSaving}
                      >
                        ⇄ {isSwapping ? 'Keep current' : 'Swap option'}
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn-text-action remove"
                      onClick={() => handleRemove(idx)}
                      disabled={isSaving}
                    >
                      ✕ Remove
                    </button>
                  </div>

                  {/* Inline Swap Drawer with trade-off annotations */}
                  {isSwapping && (
                    <div className="swap-drawer">
                      <div className="swap-drawer-title">
                        Choose an alternative for step {stepNumber}:
                      </div>
                      <div className="swap-options-list">
                        {itinerary.alternatives.map((alt) => {
                          const tradeOff = getTradeOffNote(alt, item.candidate);
                          return (
                            <div key={alt.option_id} className="swap-option-item">
                              <div className="swap-option-info">
                                <span className="swap-icon">
                                  {getCategoryIcon(alt.category)}
                                </span>
                                <div className="swap-details">
                                  <span className="swap-name">{alt.name}</span>
                                  <span className="swap-meta">
                                    {alt.category} · {formatCurrency(alt.cost)}
                                    {alt.duration_minutes ? ` · ${alt.duration_minutes}m` : ''}
                                  </span>
                                  <span className="trade-off-tag">{tradeOff}</span>
                                </div>
                              </div>
                              <button
                                type="button"
                                className="btn-swap-select"
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

      {/* Add option drawer if user has space and wants to add another stop */}
      {itinerary.items.length > 0 && itinerary.items.length < 3 && itinerary.alternatives.length > 0 && !showAddMenu && (
        <div className="add-option-trigger">
          <button
            type="button"
            className="btn-add-step"
            onClick={() => setShowAddMenu(true)}
            disabled={isSaving}
          >
            + Add another stop to your plan
          </button>
        </div>
      )}

      {showAddMenu && itinerary.alternatives.length > 0 && (
        <div className="add-option-drawer">
          <div className="swap-drawer-title">Select an activity or place to add:</div>
          <div className="swap-options-list">
            {itinerary.alternatives.map((alt) => (
              <div key={alt.option_id} className="swap-option-item">
                <div className="swap-option-info">
                  <span className="swap-icon">{getCategoryIcon(alt.category)}</span>
                  <div className="swap-details">
                    <span className="swap-name">{alt.name}</span>
                    <span className="swap-meta">
                      {alt.category} · {formatCurrency(alt.cost)}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-swap-select"
                  onClick={() => handleAdd(alt)}
                >
                  + Add to itinerary
                </button>
              </div>
            ))}
          </div>
          <button
            type="button"
            className="btn-text-action cancel-add"
            onClick={() => setShowAddMenu(false)}
          >
            Cancel
          </button>
        </div>
      )}

      {/* Budget Summary Bar */}
      <div className={`proposal-budget-bar ${itinerary.isOverBudget ? 'over-budget' : ''}`}>
        <div className="budget-summary-stat">
          <span className="budget-label">Estimated Total</span>
          <span className="budget-value">
            {formatCurrency(itinerary.estimatedTotal)}
          </span>
        </div>

        {itinerary.remainingBudget !== null && (
          <div className="budget-summary-stat">
            <span className="budget-label">Remaining Budget</span>
            <span
              className={`budget-value ${
                itinerary.isOverBudget ? 'negative' : 'positive'
              }`}
            >
              {itinerary.remainingBudget >= 0
                ? formatCurrency(itinerary.remainingBudget)
                : `-R${Math.abs(itinerary.remainingBudget).toFixed(0)}`}
            </span>
          </div>
        )}

        {itinerary.isOverBudget && (
          <div className="budget-warning-text">
            ⚠️ This plan exceeds your stated budget limit.
          </div>
        )}
      </div>

      {/* Conversational Plan Modification */}
      {onTweakPlan && (
        <div
          className="proposal-tweak-section"
          style={{
            marginTop: '1.5rem',
            marginBottom: '1rem',
            padding: '1rem 1.25rem',
            borderRadius: '12px',
            background: 'var(--surface-subtle, #fbfbfa)',
            border: '1px solid var(--border-subtle, #e5e5e0)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '0.6rem',
            }}
          >
            <span
              style={{
                fontSize: '0.875rem',
                fontWeight: 600,
                color: 'var(--text-secondary, #52525b)',
              }}
            >
              💬 Want to tweak this plan?
            </span>
            <small style={{ fontSize: '0.75rem', color: 'var(--text-muted, #71717a)' }}>
              Preserves your context
            </small>
          </div>

          {/* Quick adjustment chips */}
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '0.5rem',
              marginBottom: '0.75rem',
            }}
          >
            {['Make it cheaper', 'Nothing outdoors', 'Add 2 people', 'Make it Sunday'].map(
              (chip) => (
                <button
                  key={chip}
                  type="button"
                  className="chip-btn"
                  style={{
                    fontSize: '0.8rem',
                    padding: '4px 10px',
                    borderRadius: '16px',
                    border: '1px solid #d4d4d8',
                    background: '#ffffff',
                    color: '#27272a',
                    cursor: isTweaking || isSaving ? 'not-allowed' : 'pointer',
                    opacity: isTweaking || isSaving ? 0.6 : 1,
                  }}
                  disabled={isTweaking || isSaving}
                  onClick={() => onTweakPlan(chip)}
                >
                  + {chip}
                </button>
              )
            )}
          </div>

          {/* Inline custom prompt input */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (customTweak.trim() && !isTweaking && !isSaving) {
                onTweakPlan(customTweak.trim());
                setCustomTweak('');
              }
            }}
            style={{ display: 'flex', gap: '0.5rem' }}
          >
            <input
              type="text"
              value={customTweak}
              onChange={(e) => setCustomTweak(e.target.value)}
              placeholder="e.g. Make it cheaper, no outdoors, add 2 people..."
              disabled={isTweaking || isSaving}
              style={{
                flex: 1,
                fontSize: '0.85rem',
                padding: '0.45rem 0.75rem',
                borderRadius: '8px',
                border: '1px solid #d4d4d8',
                outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={!customTweak.trim() || isTweaking || isSaving}
              style={{
                fontSize: '0.85rem',
                padding: '0.45rem 1rem',
                borderRadius: '8px',
                border: 'none',
                background: '#18181b',
                color: '#fff',
                fontWeight: 500,
                cursor: !customTweak.trim() || isTweaking || isSaving ? 'not-allowed' : 'pointer',
                opacity: !customTweak.trim() || isTweaking || isSaving ? 0.5 : 1,
              }}
            >
              {isTweaking ? 'Updating...' : 'Tweak'}
            </button>
          </form>
        </div>
      )}

      {/* Bottom Actions */}
      <div className="proposal-actions">
        <button
          type="button"
          className="btn-primary-confirm"
          onClick={handleConfirmClick}
          disabled={isSaving || isTweaking || itinerary.items.length === 0}
        >
          {isSaving ? (
            <span className="spinner-wrap">
              <span className="spinner small" />
              Saving your plan...
            </span>
          ) : (
            'Looks good'
          )}
        </button>

        {itinerary.alternatives.length > 0 && !showAddMenu && (
          <button
            type="button"
            className="btn-secondary-custom"
            onClick={() => {
              if (swappingIndex === null && itinerary.items.length > 0) {
                setSwappingIndex(0);
              } else {
                setShowAddMenu(true);
              }
            }}
            disabled={isSaving}
          >
            Change something
          </button>
        )}

        <button
          type="button"
          className="btn-link"
          onClick={onModifyIntent}
          disabled={isSaving}
        >
          Try a different request
        </button>
      </div>

      {itinerary.attribution && (
        <div
          style={{
            marginTop: '1.25rem',
            textAlign: 'center',
            fontSize: '0.72rem',
            color: '#71717a',
          }}
        >
          Map and place information {itinerary.attribution}
        </div>
      )}
    </div>
  );
};
