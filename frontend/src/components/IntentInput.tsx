import React, { useState, useRef, useImperativeHandle, forwardRef } from 'react';
import { IconArrowRight, IconSparkles, IconArrowDown } from './Icons';

export interface IntentInputHandle {
  focus: () => void;
  setIntent: (text: string) => void;
}

interface IntentInputProps {
  onSubmit: (intent: string) => void;
  isLoading: boolean;
  defaultValue?: string;
}

interface ExamplePrompt {
  label: string;
  category: string;
  emoji: string;
  subtitle: string;
  prompt: string;
}

const EXAMPLE_PROMPTS: ExamplePrompt[] = [
  {
    label: 'Cute birthday afternoon',
    category: 'Celebration',
    emoji: '🎂',
    subtitle: '4 people · Sat afternoon · Under R1,500',
    prompt: 'Plan a cute birthday afternoon for four under R1,500 in Cape Town.',
  },
  {
    label: 'Relaxed dinner date',
    category: 'Romance',
    emoji: '🍷',
    subtitle: '2 people · Good food & somewhere pretty · R800',
    prompt: 'A relaxed date with good food and somewhere pretty afterwards under R800.',
  },
  {
    label: 'Afternoon free & bored',
    category: 'Solo / Spontaneous',
    emoji: '📖',
    subtitle: '1 person · Two hours free · Coffee & read · R300',
    prompt: 'I’m bored. I have R300 and the afternoon free tomorrow to read somewhere cozy.',
  },
  {
    label: 'Quiet dark-themed lunch',
    category: 'Atmosphere',
    emoji: '🕯️',
    subtitle: '2 people · Quiet dark themed restaurant · R500',
    prompt: 'Lunch for two in a quiet dark themed restaurant, budget R500.',
  },
  {
    label: 'Rainy Saturday with kids',
    category: 'Family / Weather',
    emoji: '☔',
    subtitle: '4 people · Indoor & sheltered only · R800',
    prompt: 'Family outing with 2 kids this Saturday, indoor activities only because of bad weather, budget R800.',
  },
  {
    label: 'Scenic morning walk & pastry',
    category: 'Outdoors',
    emoji: '🌿',
    subtitle: 'Solo / duo · Unhurried stroll & bakery · ~R200',
    prompt: 'Solo morning walk somewhere scenic followed by a quiet pastry, budget R200.',
  },
];

export const IntentInput = forwardRef<IntentInputHandle, IntentInputProps>(
  ({ onSubmit, isLoading, defaultValue = '' }, ref) => {
    const [intent, setIntent] = useState(defaultValue);
    const [isFocused, setIsFocused] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    useImperativeHandle(ref, () => ({
      focus: () => {
        if (textareaRef.current) {
          textareaRef.current.focus();
          textareaRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      },
      setIntent: (text: string) => {
        setIntent(text);
        if (textareaRef.current) {
          textareaRef.current.focus();
        }
      },
    }));

    const handleSubmit = (e?: React.FormEvent) => {
      if (e) e.preventDefault();
      if (!intent.trim() || isLoading) return;
      onSubmit(intent.trim());
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    };

    const handleSelectPrompt = (promptText: string) => {
      setIntent(promptText);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    };

    const handleScrollDown = () => {
      const elem = document.getElementById('how-it-works');
      elem?.scrollIntoView({ behavior: 'smooth' });
    };

    return (
      <div id="hero-input" className="hero-section">
        {/* Brand & Editorial Hero Headline */}
        <div className="hero-content">
          <div className="hero-eyebrow animate-fade-in">
            <span className="eyebrow-pill-dot" />
            <IconSparkles size={13} className="eyebrow-icon" />
            <span>DAYFORM · GIVE SHAPE TO YOUR DAY</span>
          </div>

          <h1 className="hero-heading animate-fade-up">
            Tell me what you want to do.
            <br />
            <span className="hero-heading-secondary">I’ll figure out the rest.</span>
          </h1>

          <p className="hero-description animate-fade-up delay-1">
            Skip the 15 open browser tabs, the spreadsheet of opening hours, and the budget guesswork.
            Describe your day in plain human words—Dayform evaluates real places, verified operating hours,
            transit times, and budgets to build an unhurried, coherent itinerary.
          </p>
        </div>

        {/* Premium Command Surface */}
        <div className={`command-surface-wrapper ${isFocused ? 'focused' : ''} animate-fade-up delay-2`}>
          <form onSubmit={handleSubmit} className="command-surface-form">
            <div className="command-input-container">
              <textarea
                ref={textareaRef}
                className="command-textarea"
                rows={3}
                value={intent}
                onChange={(e) => setIntent(e.target.value)}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                onKeyDown={handleKeyDown}
                placeholder="“Plan a cute birthday afternoon for four under R1,500” or “I’m bored. I have R300 and the afternoon free...”"
                disabled={isLoading}
              />
            </div>

            <div className="command-surface-footer">
              <div className="command-helper-text">
                <span className="keyboard-hint">Press ↵ Enter to plan</span>
              </div>

              <button
                type="submit"
                className="command-submit-button"
                disabled={isLoading || !intent.trim()}
                aria-label="Generate plan"
              >
                {isLoading ? (
                  <span className="button-loading-state">
                    <span className="loading-spinner" />
                    <span>Giving shape...</span>
                  </span>
                ) : (
                  <span className="button-label-state">
                    <span>Give it shape</span>
                    <IconArrowRight size={16} className="button-arrow" />
                  </span>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Curated Suggestion Chips */}
        <div className="suggestion-section animate-fade-up delay-3">
          <div className="suggestion-label-row">
            <span className="suggestion-label">Or click an idea to start:</span>
          </div>
          <div className="suggestion-grid">
            {EXAMPLE_PROMPTS.map((item) => {
              const isSelected = intent === item.prompt;
              return (
                <button
                  key={item.label}
                  type="button"
                  className={`suggestion-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleSelectPrompt(item.prompt)}
                  disabled={isLoading}
                >
                  <div className="suggestion-card-header">
                    <span className="suggestion-emoji">{item.emoji}</span>
                    <span className="suggestion-title">{item.label}</span>
                    <span className="suggestion-category-tag">{item.category}</span>
                  </div>
                  <span className="suggestion-subtitle">{item.subtitle}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Scroll Cue */}
        <div className="hero-scroll-cue" onClick={handleScrollDown} role="button" tabIndex={0}>
          <span className="cue-label">See how Dayform thinks</span>
          <IconArrowDown size={14} className="cue-arrow-icon" />
        </div>
      </div>
    );
  }
);

IntentInput.displayName = 'IntentInput';
