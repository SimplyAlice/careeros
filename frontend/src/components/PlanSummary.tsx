import React, { useEffect, useState } from 'react';
import type {
  ExecutionActionRead,
  PlanActionsRead,
  PlanRead,
} from '../types/planning';
import {
  completePlanItem,
  executePlanAction,
  getPlanActions,
  uncompletePlanItem,
} from '../api/planning';
import { getCategoryIcon } from '../utils/itineraryBuilder';

interface PlanSummaryProps {
  plan: PlanRead;
  onStartNew?: () => void;
  onTweakPlan?: (tweakText: string) => Promise<void>;
  isTweaking?: boolean;
}

export const PlanSummary: React.FC<PlanSummaryProps> = ({
  plan,
  onStartNew,
  onTweakPlan,
  isTweaking = false,
}) => {
  const [tweakInput, setTweakInput] = useState('');
  const [planActions, setPlanActions] = useState<PlanActionsRead | null>(null);
  const [executingActionId, setExecutingActionId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{
    message: string;
    type: 'info' | 'success' | 'error';
  } | null>(null);

  const formatCurrency = (val: string | number | null | undefined) => {
    if (val === null || val === undefined) return '—';
    const num = typeof val === 'number' ? val : parseFloat(val);
    return isNaN(num) ? String(val) : `R${num.toFixed(0)}`;
  };

  const remaining = plan.budget?.remaining_budget;
  const isOverBudget = plan.budget?.is_over_budget;
  const groupSize = plan.context?.group_size || 1;
  const groupLabel = groupSize > 1 ? `${groupSize} people` : 'Solo';

  // Load execution actions whenever plan changes
  const fetchActions = async () => {
    try {
      const actionsData = await getPlanActions(plan.id);
      setPlanActions(actionsData);
    } catch (err) {
      console.error('Failed to load plan execution actions:', err);
    }
  };

  useEffect(() => {
    fetchActions();
  }, [plan.id, plan.updated_at, plan.items.length]);

  const handleActionClick = async (itemId: string, action: ExecutionActionRead) => {
    setExecutingActionId(action.id);
    try {
      if (action.action_type === 'mark_complete') {
        const itemActions = planActions?.items.find((i) => i.item_id === itemId);
        const isCurrentlyCompleted = itemActions?.item_status === 'completed';

        if (isCurrentlyCompleted) {
          await uncompletePlanItem(plan.id, itemId);
          setFeedback({
            message: 'Marked stop as planned.',
            type: 'info',
          });
        } else {
          await completePlanItem(plan.id, itemId);
          setFeedback({
            message: 'Marked stop as completed.',
            type: 'success',
          });
        }
        await fetchActions();
        return;
      }

      // External Navigation Actions: Website, Directions, Reserve, Calendar
      if (action.target_url) {
        if (action.action_type === 'call') {
          window.location.href = action.target_url;
        } else {
          window.open(action.target_url, '_blank', 'noopener,noreferrer');
        }
      }

      // Call execution endpoint to log action and obtain honest narrative message
      const result = await executePlanAction(
        plan.id,
        itemId,
        action.action_type,
        action.target_url
      );

      const feedbackType =
        result.status === 'failed' || result.status === 'unavailable'
          ? 'error'
          : result.action_type === 'reserve'
          ? 'info'
          : 'success';

      setFeedback({
        message: result.message,
        type: feedbackType,
      });

      await fetchActions();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Action could not be completed.';
      setFeedback({
        message: `Execution issue: ${msg}`,
        type: 'error',
      });
    } finally {
      setExecutingActionId(null);
    }
  };

  // Derive plan progression status
  const planProgression = planActions?.plan_status || 'ready';
  const completedStopsCount =
    planActions?.items.filter((i) => i.item_status === 'completed').length || 0;

  return (
    <div className="plan-summary-card">
      {/* Execution Feedback Notification */}
      {feedback && (
        <div className={`execution-feedback-toast ${feedback.type}`}>
          <span>{feedback.message}</span>
          <button
            type="button"
            className="execution-feedback-close"
            onClick={() => setFeedback(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* Header with Ownership & Progression status */}
      <div className="summary-header">
        <div className="summary-title-wrap">
          <div className="confirmed-badge-row">
            <span className="summary-badge confirmed">✓ Saved to OpsOS</span>
            {planProgression === 'completed' ? (
              <span className="status-pill completed">✓ Plan Completed</span>
            ) : planProgression === 'in_progress' ? (
              <span className="status-pill in-progress">
                In Progress ({completedStopsCount} of {plan.items.length} done)
              </span>
            ) : (
              <span className="status-pill ready">Active Plan</span>
            )}
          </div>
          <h2 className="summary-title">{plan.title || 'Your Confirmed Itinerary'}</h2>
          <p className="summary-intention">“{plan.intention}”</p>
        </div>

        <div className="summary-meta-pills">
          {plan.context?.location && (
            <span className="context-pill">📍 {plan.context.location}</span>
          )}
          <span className="context-pill">👥 {groupLabel}</span>
        </div>
      </div>

      {/* Budget Overview Widget */}
      {plan.budget && (
        <div className={`budget-widget ${isOverBudget ? 'over-budget' : ''}`}>
          <div className="budget-stat">
            <span className="stat-label">Budget Limit</span>
            <span className="stat-value">
              {formatCurrency(plan.budget.budget_maximum)}
            </span>
          </div>
          <div className="budget-stat">
            <span className="stat-label">Total Planned</span>
            <span className="stat-value planned">
              {formatCurrency(plan.budget.total_planned_cost)}
            </span>
          </div>
          <div className="budget-stat">
            <span className="stat-label">Remaining</span>
            <span className={`stat-value remaining ${isOverBudget ? 'negative' : 'positive'}`}>
              {formatCurrency(remaining)}
            </span>
          </div>
          {isOverBudget && (
            <div className="over-budget-warning">
              ⚠️ Warning: Your selections exceed the stated budget limit.
            </div>
          )}
        </div>
      )}

      {/* Confirmed Timeline Itinerary with Real-World Actions */}
      <div className="itinerary-section">
        <h3 className="itinerary-title">
          Itinerary & Actions ({plan.items.length} {plan.items.length === 1 ? 'stop' : 'stops'})
        </h3>

        {plan.items.length === 0 ? (
          <div className="empty-itinerary">
            <p>No items in this plan.</p>
          </div>
        ) : (
          <div className="itinerary-list">
            {plan.items.map((item, idx) => {
              const stepNumber = String(idx + 1).padStart(2, '0');
              const itemActionsData = planActions?.items.find((i) => i.item_id === item.id);
              const isItemCompleted = itemActionsData?.item_status === 'completed';
              const actions = itemActionsData?.actions || [];

              return (
                <div
                  key={item.id || idx}
                  className={`itinerary-item ${isItemCompleted ? 'completed-item' : ''}`}
                >
                  <div className="itinerary-item-left" style={{ flex: 1 }}>
                    <span className="item-position">{stepNumber}</span>
                    <div className="item-info" style={{ width: '100%' }}>
                      <div className="item-name-row" style={{ justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span className="item-icon">{getCategoryIcon(item.item_type)}</span>
                          <span
                            className="item-name"
                            style={{
                              textDecoration: isItemCompleted ? 'line-through' : 'none',
                              color: isItemCompleted ? '#71717a' : 'inherit',
                            }}
                          >
                            {item.name}
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <span
                            className={`item-status-tag ${
                              isItemCompleted ? 'completed' : 'planned'
                            }`}
                          >
                            {isItemCompleted ? '✓ Completed' : 'Planned'}
                          </span>
                          <span className="item-cost">
                            {formatCurrency(item.estimated_cost)}
                          </span>
                        </div>
                      </div>

                      <div className="item-meta">
                        <span className="item-type-tag">{item.item_type}</span>
                        {item.duration_minutes && (
                          <span className="item-duration">⏱ {item.duration_minutes}m</span>
                        )}
                        {item.location && (
                          <span className="item-loc">📍 {item.location}</span>
                        )}
                      </div>

                      {/* Execution Actions for this Stop */}
                      {actions.length > 0 && (
                        <div className="item-actions-wrapper">
                          {actions.map((act) => {
                            const isBusy = executingActionId === act.id;
                            let btnClass = 'action-btn';
                            let icon = '';

                            if (act.action_type === 'open_website') {
                              icon = '🌐';
                            } else if (act.action_type === 'directions') {
                              icon = '🗺️';
                            } else if (act.action_type === 'call') {
                              icon = '📞';
                            } else if (act.action_type === 'reserve') {
                              icon = '📅';
                              btnClass += ' action-reserve';
                            } else if (act.action_type === 'add_to_calendar') {
                              icon = '🗓️';
                            } else if (act.action_type === 'mark_complete') {
                              if (isItemCompleted) {
                                icon = '↩️';
                                btnClass += ' action-undo';
                              } else {
                                icon = '✓';
                                btnClass += ' action-complete';
                              }
                            }

                            return (
                              <button
                                key={act.id}
                                type="button"
                                className={btnClass}
                                disabled={isBusy}
                                onClick={() => handleActionClick(item.id, act)}
                                title={act.description || act.label}
                              >
                                <span>{icon}</span>
                                <span>{isBusy ? 'Opening...' : act.label}</span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Conversational Tweak: Something changed? (Adaptive Loop - Scenario H) */}
      {onTweakPlan && (
        <div
          style={{
            marginTop: '28px',
            padding: '18px 20px',
            background: '#fafafa',
            borderRadius: '12px',
            border: '1px solid #e4e4e7',
          }}
        >
          <div
            style={{
              fontSize: '0.88rem',
              fontWeight: 600,
              color: '#18181b',
              marginBottom: '4px',
            }}
          >
            💬 Something changed or venue unavailable?
          </div>
          <p style={{ fontSize: '0.78rem', color: '#71717a', margin: '0 0 10px 0' }}>
            e.g. “Kloof Street House is fully booked”, “Actually we can only leave at 2”, or “Keep it under R600”
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (tweakInput.trim() && !isTweaking) {
                onTweakPlan(tweakInput.trim());
              }
            }}
            style={{ display: 'flex', gap: '8px' }}
          >
            <input
              type="text"
              value={tweakInput}
              onChange={(e) => setTweakInput(e.target.value)}
              placeholder="Tell me what changed..."
              disabled={isTweaking}
              style={{
                flex: 1,
                fontSize: '0.85rem',
                padding: '0.55rem 0.85rem',
                borderRadius: '8px',
                border: '1px solid #d4d4d8',
                outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={!tweakInput.trim() || isTweaking}
              style={{
                fontSize: '0.85rem',
                padding: '0.55rem 1.1rem',
                borderRadius: '8px',
                border: 'none',
                background: '#18181b',
                color: '#fff',
                fontWeight: 500,
                cursor: !tweakInput.trim() || isTweaking ? 'not-allowed' : 'pointer',
                opacity: !tweakInput.trim() || isTweaking ? 0.5 : 1,
              }}
            >
              {isTweaking ? 'Adapting...' : 'Adapt plan'}
            </button>
          </form>
        </div>
      )}

      {/* Plan Something Else Action */}
      {onStartNew && (
        <div className="summary-footer-actions">
          <button type="button" className="btn-secondary-custom" onClick={onStartNew}>
            + Plan something else
          </button>
        </div>
      )}
    </div>
  );
};
