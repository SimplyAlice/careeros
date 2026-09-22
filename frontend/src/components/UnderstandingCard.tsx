import React from 'react';
import type { PlanRead } from '../types/planning';
import { formatCurrency } from '../utils/itineraryBuilder';

interface UnderstandingCardProps {
  plan: PlanRead;
  budgetMax: number | null;
}

export const UnderstandingCard: React.FC<UnderstandingCardProps> = ({ plan, budgetMax }) => {
  const location = plan.context?.location || 'Cape Town';
  const groupSize = plan.context?.group_size || 1;
  const groupLabel = groupSize > 1 ? `${groupSize} people` : 'Solo';

  // Detect natural day/timing clues from intention if present
  const lowerIntent = plan.intention.toLowerCase();
  let timeClue: string | null = null;
  if (lowerIntent.includes('saturday')) timeClue = 'Saturday';
  else if (lowerIntent.includes('sunday')) timeClue = 'Sunday';
  else if (lowerIntent.includes('weekend')) timeClue = 'This weekend';
  else if (lowerIntent.includes('tonight')) timeClue = 'Tonight';
  else if (lowerIntent.includes('afternoon')) timeClue = 'Afternoon';
  else if (lowerIntent.includes('evening')) timeClue = 'Evening';

  // Derive conversational constraints
  const keepingItPoints: string[] = [];
  if (budgetMax !== null) {
    keepingItPoints.push(`Under ${formatCurrency(budgetMax)}`);
  }
  keepingItPoints.push(`Suitable for ${groupLabel.toLowerCase()}`);
  if (location) {
    keepingItPoints.push(`In ${location}`);
  }
  keepingItPoints.push('Balanced and unhurried');

  return (
    <div className="understanding-card">
      <div className="understanding-top">
        <span className="understanding-badge">Understood</span>
        <h3 className="understanding-heading">Got it. Here’s what I’m working with:</h3>
      </div>

      {/* Inferred Context Chips */}
      <div className="understanding-chips">
        {timeClue && <span className="context-chip time">📅 {timeClue}</span>}
        {location && <span className="context-chip location">📍 {location}</span>}
        <span className="context-chip group">👥 {groupLabel}</span>
        {budgetMax !== null && (
          <span className="context-chip budget">💰 Under {formatCurrency(budgetMax)}</span>
        )}
      </div>

      {/* Synthesis */}
      <div className="understanding-body">
        <div className="understanding-field">
          <span className="field-label">You want</span>
          <p className="field-quote">“{plan.intention}”</p>
        </div>

        <div className="understanding-field">
          <span className="field-label">Keeping it</span>
          <div className="keeping-it-pills">
            {keepingItPoints.map((point, idx) => (
              <span key={idx} className="keeping-pill">
                ✓ {point}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
