import React, { useState, useRef, useImperativeHandle, forwardRef } from 'react';
import { IconArrowRight, IconArrowDown } from './Icons';

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
  tag: string;
  title: string;
  meta: string;
  prompt: string;
}

const EDITORIAL_PROMPTS: ExamplePrompt[] = [
  {
    tag: 'CELEBRATION',
    title: 'Cute birthday dinner for four',
    meta: 'Sat evening · Cape Town · Under R1,500',
    prompt: 'Plan a cute birthday afternoon for four under R1,500 in Cape Town.',
  },
  {
    tag: 'ROMANCE',
    title: 'Relaxed dinner date & pretty walk',
    meta: '2 people · Good food & unhurried · R800',
    prompt: 'A relaxed date with good food and somewhere pretty afterwards under R800.',
  },
  {
    tag: 'SPONTANEOUS',
    title: 'Afternoon free, coffee & read',
    meta: 'Solo · Two hours free · Under R300',
    prompt: 'I’m bored. I have R300 and the afternoon free tomorrow to read somewhere cozy.',
  },
  {
    tag: 'ATMOSPHERE',
    title: 'Quiet dark-themed restaurant',
    meta: '2 people · Lunch & scenery · Budget R500',
    prompt: 'Lunch for two in a quiet dark themed restaurant, budget R500.',
  },
  {
    tag: 'WEATHER',
    title: 'Rainy Saturday with 2 kids',
    meta: '4 people · Sheltered indoors only · R800',
    prompt: 'Family outing with 2 kids this Saturday, indoor activities only because of bad weather, budget R800.',
  },
  {
    tag: 'CULTURE',
    title: 'Historic walk & artisan coffee',
    meta: 'Solo / duo · Local craft & bites · R250',
    prompt: 'An afternoon exploring local culture, historic streets, and craft food markets.',
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
      <section id="hero-input" className="hero-editorial-stage">
        <div className="hero-stage-container">
          {/* Massive Brand Masthead */}
          <div className="hero-brand-masthead">
            <span className="masthead-name">DAYFORM</span>
            <span className="masthead-edition">EDITION 2026 · ISSUE NO. 12</span>
          </div>

          {/* Dramatic Hero Content Block */}
          <div className="hero-headline-block">
            <div className="hero-tag-row">
              <span className="hero-tag-pill">REAL-WORLD PLANNING ENGINE</span>
              <span className="hero-tag-location">CAPE TOWN & SURROUNDS</span>
            </div>

            <h1 className="hero-editorial-title">
              Give shape <br />
              <em>to your day.</em>
            </h1>

            <div className="hero-promise-callout">
              <p className="hero-promise-lead">
                Tell me what you want to do. <br />
                <span className="hero-promise-accent">I’ll figure out the rest.</span>
              </p>
              <p className="hero-promise-sub">
                No 15 open tabs. No manual spreadsheet of closing times. No budget guesswork.
                Describe your day in human words—Dayform evaluates real places, verified operating hours,
                transit times, and budgets to compose an unhurried, coherent journey.
              </p>
            </div>
          </div>

          {/* High-Contrast Command Surface */}
          <div className={`hero-command-container ${isFocused ? 'focused' : ''}`}>
            <form onSubmit={handleSubmit} className="hero-command-form">
              <div className="hero-command-box command-input-slot">
                <label htmlFor="intent-input" className="command-input-label">
                  ENTER INTENTION / MOOD / CONSTRAINTS:
                </label>
                <textarea
                  id="intent-input"
                  ref={textareaRef}
                  className="hero-command-textarea"
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

              <div className="hero-command-action-row command-footer-strip">
                <span className="command-key-hint">PRESS ↵ ENTER TO GENERATE</span>

                <button
                  type="submit"
                  className="hero-command-cta"
                  disabled={isLoading || !intent.trim()}
                  aria-label="Generate itinerary"
                >
                  {isLoading ? (
                    <span className="cta-loading-state">
                      <span className="cta-spinner" />
                      <span>COMPOSING ITINERARY...</span>
                    </span>
                  ) : (
                    <span className="cta-label-state">
                      <span>GIVE IT SHAPE</span>
                      <IconArrowRight size={16} className="cta-arrow" />
                    </span>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Discovery & Plan Ideas Matrix Grid (2-column on desktop, structured matrix) */}
          <div className="hero-curated-prompts">
            <div className="curated-prompts-header">
              <span className="prompts-kicker">DISCOVERY & PLAN IDEAS</span>
              <span className="prompts-hint">Select a starting point to compose your plan</span>
            </div>

            <div className="discovery-matrix-grid">
              {EDITORIAL_PROMPTS.map((item) => {
                const isSelected = intent === item.prompt;
                return (
                  <button
                    key={item.title}
                    type="button"
                    className={`discovery-matrix-cell ${isSelected ? 'active' : ''}`}
                    onClick={() => handleSelectPrompt(item.prompt)}
                    disabled={isLoading}
                  >
                    <div className="discovery-cell-top">
                      <span className="discovery-cell-tag">{item.tag}</span>
                      <span className="discovery-cell-cue">Use idea ↗</span>
                    </div>
                    <h3 className="discovery-cell-title">{item.title}</h3>
                    <p className="discovery-cell-meta">{item.meta}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Scroll Cue to Engine Mechanics */}
          <button
            type="button"
            className="hero-scroll-invite hero-scroll-trigger"
            onClick={handleScrollDown}
            aria-label="Scroll to how it works"
          >
            <span className="invite-label scroll-label">HOW THE ENGINE THINKS</span>
            <IconArrowDown size={14} className="invite-arrow-icon scroll-icon" />
          </button>
        </div>
      </section>
    );
  }
);

IntentInput.displayName = 'IntentInput';
