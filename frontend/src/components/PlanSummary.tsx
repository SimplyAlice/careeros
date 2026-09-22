import React from 'react';
import type { PlanRead } from '../types/planning';

interface PlanSummaryProps {
  plan: PlanRead;
}

export const PlanSummary: React.FC<PlanSummaryProps> = ({ plan }) => {
  const formatCurrency = (val: string | number | null | undefined) => {
    if (val === null || val === undefined) return '—';
    const num = typeof val === 'number' ? val : parseFloat(val);
    return isNaN(num) ? String(val) : `R${num.toFixed(2)}`;
  };

  const remaining = plan.budget?.remaining_budget;
  const isOverBudget = plan.budget?.is_over_budget;

  return (
    <div className="plan-summary-card">
      <div className="summary-header">
        <div className="summary-title-wrap">
          <span className="summary-badge">Active Plan</span>
          <h3 className="summary-title">{plan.title || 'Your Curated Plan'}</h3>
          <p className="summary-intention">“{plan.intention}”</p>
        </div>
        <div className="summary-meta-pills">
          {plan.context?.location && (
            <span className="context-pill">📍 {plan.context.location}</span>
          )}
          {plan.context?.group_size && (
            <span className="context-pill">👥 {plan.context.group_size} people</span>
          )}
          <span className={`status-pill ${plan.status}`}>
            {plan.status.toUpperCase()}
          </span>
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

      {/* Selected Items Itinerary */}
      <div className="itinerary-section">
        <h4 className="itinerary-title">
          Selected Items ({plan.items.length})
        </h4>

        {plan.items.length === 0 ? (
          <div className="empty-itinerary">
            <p>No items added yet. Click “+ Add to plan” on any recommendation below to build your itinerary.</p>
          </div>
        ) : (
          <div className="itinerary-list">
            {plan.items.map((item, idx) => (
              <div key={item.id || idx} className="itinerary-item">
                <div className="itinerary-item-left">
                  <span className="item-position">{idx + 1}</span>
                  <div className="item-info">
                    <span className="item-name">{item.name}</span>
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
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
