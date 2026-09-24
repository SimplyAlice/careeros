import React, { useState } from 'react';
import type { PlanRead } from '../types/planning';
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
  const formatCurrency = (val: string | number | null | undefined) => {
    if (val === null || val === undefined) return '—';
    const num = typeof val === 'number' ? val : parseFloat(val);
    return isNaN(num) ? String(val) : `R${num.toFixed(0)}`;
  };

  const remaining = plan.budget?.remaining_budget;
  const isOverBudget = plan.budget?.is_over_budget;
  const groupSize = plan.context?.group_size || 1;
  const groupLabel = groupSize > 1 ? `${groupSize} people` : 'Solo';

  return (
    <div className="plan-summary-card">
      {/* Header with Ownership & Saved status */}
      <div className="summary-header">
        <div className="summary-title-wrap">
          <div className="confirmed-badge-row">
            <span className="summary-badge confirmed">✓ Saved to OpsOS</span>
            <span className="status-pill ready">Active Plan</span>
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

      {/* Confirmed Timeline Itinerary */}
      <div className="itinerary-section">
        <h3 className="itinerary-title">
          Itinerary ({plan.items.length} {plan.items.length === 1 ? 'stop' : 'stops'})
        </h3>

        {plan.items.length === 0 ? (
          <div className="empty-itinerary">
            <p>No items in this plan.</p>
          </div>
        ) : (
          <div className="itinerary-list">
            {plan.items.map((item, idx) => {
              const stepNumber = String(idx + 1).padStart(2, '0');
              return (
                <div key={item.id || idx} className="itinerary-item">
                  <div className="itinerary-item-left">
                    <span className="item-position">{stepNumber}</span>
                    <div className="item-info">
                      <div className="item-name-row">
                        <span className="item-icon">{getCategoryIcon(item.item_type)}</span>
                        <span className="item-name">{item.name}</span>
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
                    </div>
                  </div>
                  <div className="itinerary-item-right">
                    <span className="item-cost">
                      {formatCurrency(item.estimated_cost)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Conversational Tweak: Something changed? */}
      {onTweakPlan && (
        <div style={{ marginTop: '24px', padding: '16px', background: '#fafafa', borderRadius: '12px', border: '1px solid #e4e4e7' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#18181b', marginBottom: '4px' }}>
            💬 Something changed?
          </div>
          <p style={{ fontSize: '0.78rem', color: '#71717a', margin: '0 0 10px 0' }}>
            e.g. “Actually we can only leave at 2”, “Keep it under R600”, or “Two more friends are coming”
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
                padding: '0.5rem 0.85rem',
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
                padding: '0.5rem 1.1rem',
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
