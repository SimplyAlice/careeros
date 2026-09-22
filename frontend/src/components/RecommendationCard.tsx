import React from 'react';
import type { DecisionCandidateRead } from '../types/planning';

interface RecommendationCardProps {
  candidate: DecisionCandidateRead;
  onSelect: (candidate: DecisionCandidateRead) => void;
  isAdding: boolean;
  isAdded: boolean;
}

export const RecommendationCard: React.FC<RecommendationCardProps> = ({
  candidate,
  onSelect,
  isAdding,
  isAdded,
}) => {
  const formatCost = (cost: string | number | null) => {
    if (cost === null || cost === undefined) return 'Free';
    const num = typeof cost === 'number' ? cost : parseFloat(cost);
    return isNaN(num) ? String(cost) : `R${num.toFixed(0)}`;
  };

  return (
    <div className={`recommendation-card ${!candidate.is_eligible ? 'ineligible' : ''} ${isAdded ? 'added' : ''}`}>
      <div className="card-top">
        <div className="card-meta">
          <span className="category-badge">{candidate.category}</span>
          <span className="type-badge">{candidate.option_type}</span>
          {candidate.location && <span className="location-badge">📍 {candidate.location}</span>}
        </div>
        <div className="card-score">
          <span className="score-number">{candidate.score}</span>
          <span className="score-label">pts match</span>
        </div>
      </div>

      <h3 className="card-name">{candidate.name}</h3>

      <div className="card-details-row">
        <div className="detail-item">
          <span className="detail-label">Cost</span>
          <span className="detail-value cost-value">{formatCost(candidate.cost)}</span>
        </div>
        {candidate.duration_minutes && (
          <div className="detail-item">
            <span className="detail-label">Duration</span>
            <span className="detail-value">{candidate.duration_minutes} mins</span>
          </div>
        )}
        <div className="detail-item">
          <span className="detail-label">Source</span>
          <span className="detail-value source-text">{candidate.source}</span>
        </div>
      </div>

      {/* Explainable Reasons */}
      {candidate.reasons && candidate.reasons.length > 0 && (
        <div className="reasons-block">
          <span className="reasons-heading">Why this works:</span>
          <ul className="reasons-list">
            {candidate.reasons.map((reason, idx) => (
              <li
                key={idx}
                className={`reason-pill ${reason.outcome}`}
              >
                <span className="reason-indicator">
                  {reason.outcome === 'supported' ? '✓' : reason.outcome === 'violated' ? '✕' : '•'}
                </span>
                <span className="reason-message">{reason.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Action */}
      <div className="card-footer">
        {isAdded ? (
          <div className="added-badge">
            <span className="checkmark">✓</span> Added to plan
          </div>
        ) : (
          <button
            type="button"
            className="add-button"
            onClick={() => onSelect(candidate)}
            disabled={isAdding || !candidate.is_eligible}
          >
            {isAdding ? (
              <span className="spinner-wrap">
                <span className="spinner small" />
                Adding...
              </span>
            ) : candidate.is_eligible ? (
              '+ Add to plan'
            ) : (
              'Ineligible'
            )}
          </button>
        )}
      </div>
    </div>
  );
};
