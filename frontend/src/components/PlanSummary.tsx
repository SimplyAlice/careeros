import React from 'react';
import type { PlanRead } from '../types/planning';
import { getCategoryIcon } from '../utils/itineraryBuilder';

interface PlanSummaryProps {
  plan: PlanRead;
  onStartNew?: () => void;
}

export const PlanSummary: React.FC<PlanSummaryProps> = ({ plan, onStartNew }) => {
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
