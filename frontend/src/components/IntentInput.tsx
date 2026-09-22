import React, { useState } from 'react';

interface IntentInputProps {
  onSubmit: (intent: string) => void;
  isLoading: boolean;
  defaultValue?: string;
}

interface ExamplePrompt {
  label: string;
  prompt: string;
}

const EXAMPLE_PROMPTS: ExamplePrompt[] = [
  {
    label: 'Plan a date',
    prompt: 'I want a nice date with my partner in Cape Town under R800.',
  },
  {
    label: 'Plan a day out',
    prompt: 'Something fun with 3 friends in Cape Town under R500.',
  },
  {
    label: 'Plan a birthday',
    prompt: 'A relaxed birthday celebration with 4 friends under R1000 with good food.',
  },
  {
    label: 'Find something fun',
    prompt: 'An active and scenic afternoon for 2 people in Cape Town.',
  },
  {
    label: 'Plan dinner',
    prompt: 'Dinner and a relaxed social evening with friends under R600.',
  },
  {
    label: 'Plan a weekend',
    prompt: 'A relaxing weekend day exploring local culture and food.',
  },
];

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

  const handleSelectPrompt = (promptText: string) => {
    setIntent(promptText);
  };

  return (
    <div className="hero-intent-card">
      <div className="hero-header">
        <span className="hero-tag">Intelligent Real-World Planning</span>
        <h1 className="hero-title">
          Tell me what you want to do.
          <span className="hero-title-accent"> I’ll figure out the rest.</span>
        </h1>
        <p className="hero-subtitle">
          Whether it’s a date, a birthday, dinner, or a day out with friends—describe your intention, and OpsOS will work through the options to propose a coherent, budget-aware plan.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="hero-form">
        <div className="hero-input-wrapper">
          <textarea
            className="hero-textarea"
            rows={3}
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            placeholder="e.g. I want to take my boyfriend somewhere nice this Saturday. We have R800 and neither of us drinks."
            disabled={isLoading}
          />
        </div>

        <div className="hero-form-footer">
          <div className="hero-presets">
            <span className="presets-label">Try an example:</span>
            <div className="presets-pills">
              {EXAMPLE_PROMPTS.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  className={`preset-pill ${intent === item.prompt ? 'active' : ''}`}
                  onClick={() => handleSelectPrompt(item.prompt)}
                  disabled={isLoading}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            className="hero-submit-button"
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
