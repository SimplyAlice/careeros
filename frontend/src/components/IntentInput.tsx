import React, { useState } from 'react';

interface IntentInputProps {
  onSubmit: (intent: string) => void;
  isLoading: boolean;
  defaultValue?: string;
}

export const IntentInput: React.FC<IntentInputProps> = ({
  onSubmit,
  isLoading,
  defaultValue = 'Something fun with 3 friends in Cape Town under R500',
}) => {
  const [intent, setIntent] = useState(defaultValue);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!intent.trim() || isLoading) return;
    onSubmit(intent.trim());
  };

  return (
    <div className="intent-card">
      <div className="intent-header">
        <span className="intent-tag">Intelligent Real-World Planning</span>
        <h2 className="intent-title">What do you want to do?</h2>
        <p className="intent-subtitle">
          Tell OpsOS your intention, who you’re with, and your constraints. We’ll figure out the rest.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="intent-form">
        <div className="intent-input-wrapper">
          <textarea
            className="intent-textarea"
            rows={3}
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            placeholder="e.g. Something fun with 3 friends in Cape Town under R500"
            disabled={isLoading}
          />
        </div>

        <div className="intent-actions">
          <div className="intent-presets">
            <span className="preset-label">Try:</span>
            <button
              type="button"
              className="preset-pill"
              onClick={() => setIntent('Something fun with 3 friends in Cape Town under R500')}
              disabled={isLoading}
            >
              Cape Town Outing (R500)
            </button>
            <button
              type="button"
              className="preset-pill"
              onClick={() => setIntent('Relaxing cultural afternoon in Bo-Kaap for 2')}
              disabled={isLoading}
            >
              Cultural Afternoon
            </button>
          </div>

          <button
            type="submit"
            className="plan-button"
            disabled={isLoading || !intent.trim()}
          >
            {isLoading ? (
              <span className="spinner-wrap">
                <span className="spinner" />
                Planning...
              </span>
            ) : (
              'Plan it'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
