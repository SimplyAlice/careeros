import React from 'react';
import type { PlanRead } from '../types/planning';
import { formatCurrency } from '../utils/itineraryBuilder';

interface UnderstandingCardProps {
  plan: PlanRead;
  budgetMax: number | null;
}

export const UnderstandingCard: React.FC<UnderstandingCardProps> = ({ plan, budgetMax }) => {
  const u = plan.understanding;

  // Occasion label
  const occasionMap: Record<string, string> = {
    date: '🥂 Date',
    birthday: '🎂 Birthday',
    celebration: '🎉 Celebration',
    friends: '👥 Outing with Friends',
    casual_hangout: '☕ Casual Hangout',
    family: '🏡 Family Outing',
    solo: '👤 Solo Outing',
  };
  const occasionLabel = u?.occasion ? occasionMap[u.occasion] || `✨ ${u.occasion}` : null;

  // People & Group
  const groupSize = u?.people_count ?? plan.context?.group_size ?? 1;
  const relContext = u?.relationship_context;
  let groupLabel = groupSize > 1 ? `${groupSize} people` : 'Solo';
  if (relContext && groupSize === 2) {
    if (relContext === 'boyfriend') groupLabel = '2 people · Boyfriend';
    else if (relContext === 'girlfriend') groupLabel = '2 people · Girlfriend';
    else if (relContext === 'partner') groupLabel = '2 people · Partner';
    else if (relContext === 'couple') groupLabel = 'Couple (2)';
  } else if (relContext && relContext === 'friends') {
    groupLabel = groupSize > 1 ? `${groupSize} friends` : 'Friends';
  }

  // Date and Timing
  const dateSpec = u?.date_spec;
  const timeWindow = u?.time_window;
  let timeLabel: string | null = null;
  if (dateSpec && timeWindow) {
    timeLabel = `${dateSpec} · ${timeWindow.charAt(0).toUpperCase() + timeWindow.slice(1)}`;
  } else if (dateSpec) {
    timeLabel = dateSpec;
  } else if (timeWindow) {
    timeLabel = timeWindow.charAt(0).toUpperCase() + timeWindow.slice(1);
  }

  // Location
  const location = u?.location || plan.context?.location || 'Cape Town';
  const locationIsDefault = u ? u.location_is_inferred : false;

  // Budget
  let budgetLabel: string | null = null;
  const budgetVal = u?.budget_amount ? Number(u.budget_amount) : budgetMax;
  if (budgetVal !== null && budgetVal > 0) {
    if (u?.budget_kind === 'approximate') {
      budgetLabel = `~${formatCurrency(budgetVal)} (approx)`;
    } else {
      budgetLabel = `Under ${formatCurrency(budgetVal)}`;
    }
  } else if (u?.budget_kind === 'preference') {
    budgetLabel = 'Budget-conscious';
  }

  // Keeping it pills (Preferences + Exclusions)
  const keepingItPoints: { label: string; isExclusion?: boolean }[] = [];

  // Exclusions first (hard constraints)
  if (u?.exclusions && u.exclusions.length > 0) {
    for (const excl of u.exclusions) {
      if (excl === 'not_too_fancy') keepingItPoints.push({ label: 'Nothing too fancy', isExclusion: true });
      else if (excl === 'no_outdoors') keepingItPoints.push({ label: 'No outdoor activities', isExclusion: true });
      else if (excl === 'no_clubs') keepingItPoints.push({ label: 'No clubs / nightlife', isExclusion: true });
      else if (excl === 'nothing_expensive') keepingItPoints.push({ label: 'Not expensive', isExclusion: true });
      else keepingItPoints.push({ label: excl.replace(/_/g, ' '), isExclusion: true });
    }
  }

  // Soft preferences
  if (u?.preferences && u.preferences.length > 0) {
    for (const pref of u.preferences) {
      if (pref === 'casual') keepingItPoints.push({ label: 'Casual & relaxed vibe' });
      else if (pref === 'nice') keepingItPoints.push({ label: 'Somewhere nice & pleasant' });
      else if (pref === 'romantic') keepingItPoints.push({ label: 'Romantic atmosphere' });
      else if (pref === 'food_focused') keepingItPoints.push({ label: 'Food-forward focus' });
      else if (pref === 'aesthetic') keepingItPoints.push({ label: 'Scenic / aesthetic spot' });
      else if (pref === 'outdoors') keepingItPoints.push({ label: 'Outdoor setting' });
      else if (pref === 'cultural') keepingItPoints.push({ label: 'Cultural highlights' });
      else keepingItPoints.push({ label: pref });
    }
  }

  // Fallback defaults if no preferences were stated
  if (keepingItPoints.length === 0) {
    if (budgetVal !== null) {
      keepingItPoints.push({ label: `Under ${formatCurrency(budgetVal)}` });
    }
    keepingItPoints.push({ label: `Suitable for ${groupLabel.toLowerCase()}` });
    if (location) {
      keepingItPoints.push({ label: `In ${location}` });
    }
    keepingItPoints.push({ label: 'Balanced and unhurried' });
  }

  return (
    <div className="understanding-card">
      <div className="understanding-top">
        <span className="understanding-badge">Understood</span>
        <h3 className="understanding-heading">Got it. Here’s what I’m working with:</h3>
      </div>

      {/* Inferred & Structured Context Chips */}
      <div className="understanding-chips">
        {occasionLabel && <span className="context-chip occasion">{occasionLabel}</span>}
        {timeLabel && <span className="context-chip time">📅 {timeLabel}</span>}
        {location && (
          <span className="context-chip location">
            📍 {location} {locationIsDefault && <small style={{ opacity: 0.7 }}>(inferred)</small>}
          </span>
        )}
        <span className="context-chip group">👥 {groupLabel}</span>
        {budgetLabel && <span className="context-chip budget">💰 {budgetLabel}</span>}
      </div>

      {/* Synthesis */}
      <div className="understanding-body">
        <div className="understanding-field">
          <span className="field-label">You want</span>
          <p className="field-quote">“{plan.intention}”</p>
        </div>

        <div className="understanding-field">
          <span className="field-label">Parameters & vibe</span>
          <div className="keeping-it-pills">
            {keepingItPoints.map((point, idx) => (
              <span
                key={idx}
                className={`keeping-pill ${point.isExclusion ? 'exclusion-pill' : ''}`}
                style={point.isExclusion ? { borderColor: '#e0a0a0', color: '#883333' } : undefined}
              >
                {point.isExclusion ? '⊘ ' : '✓ '}
                {point.label}
              </span>
            ))}
          </div>
        </div>

        {/* Ambiguities / Helpful clarifying transparency */}
        {u?.ambiguities && u.ambiguities.length > 0 && (
          <div className="understanding-ambiguity-notice" style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--text-muted, #71717a)' }}>
            {u.ambiguities.map((note, idx) => (
              <div key={idx} className="ambiguity-line">
                💡 <span style={{ fontStyle: 'italic' }}>{note}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
