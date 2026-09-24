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
  subtitle: string;
  prompt: string;
  category: string;
}

const EXAMPLE_PROMPTS: ExamplePrompt[] = [
  {
    label: 'Birthday celebration',
    category: 'Celebration',
    subtitle: '5 people · Cape Town · Sat evening · ~R1500',
    prompt: 'I want to plan a birthday dinner for 5 people in Cape Town on Saturday evening, around R1500.',
  },
  {
    label: 'Plan a date',
    category: 'Romance',
    subtitle: '2 people · Romantic dinner & stroll under R800',
    prompt: 'I want a nice date with my partner in Cape Town under R800, good food and unhurried pace.',
  },
  {
    label: 'Day out with friends',
    category: 'Social',
    subtitle: '4 people · Fun, relaxed & scenic under R500',
    prompt: 'Something fun with 3 friends in Cape Town under R500, casual vibe with good spots.',
  },
  {
    label: 'Culture & food walk',
    category: 'Discovery',
    subtitle: 'Solo / duo · Local art, history and bites',
    prompt: 'An afternoon exploring local culture, historic streets, and craft food markets.',
  },
  {
    label: 'Dinner with friends',
    category: 'Dining',
    subtitle: '4 people · Relaxed social evening under R600',
    prompt: 'Dinner and a relaxed social evening with friends under R600 total.',
  },
  {
    label: 'Active & scenic day',
    category: 'Outdoors',
    subtitle: '2 people · Ocean breeze & panoramic views',
    prompt: 'An active and scenic afternoon for 2 people in Cape Town with light food after.',
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
            <IconSparkles size={14} className="eyebrow-icon" />
            <span>DAYFORM · REAL-WORLD PLANNING</span>
          </div>

          <h1 className="hero-heading animate-fade-up">
            Tell me what you want to do.
            <br />
            <span className="hero-heading-secondary">I’ll figure out the rest.</span>
          </h1>

          <p className="hero-description animate-fade-up delay-1">
            No 15 open tabs. No manual spreadsheet of opening times. No guesswork on whether 5 friends
            can actually get dinner for R1500 on a Saturday night. Describe your intention in plain words—Dayform
            evaluates real places, verified operating hours, and live budgets to propose a coherent, timed itinerary.
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
                placeholder="e.g. Birthday dinner for 5 in Cape Town on Saturday evening around R1500, or a quiet date under R800..."
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
                    <span>Thinking...</span>
                  </span>
                ) : (
                  <span className="button-label-state">
                    <span>Plan it</span>
                    <IconArrowRight size={16} className="button-arrow" />
                  </span>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Curated Suggestion Chips */}
        <div className="suggestion-section animate-fade-up delay-3">
          <div className="suggestion-label">Or explore an intention:</div>
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
          <span className="cue-label">Explore how Dayform works</span>
          <IconArrowDown size={14} className="cue-arrow-icon" />
        </div>
      </div>
    );
  }
);

IntentInput.displayName = 'IntentInput';
