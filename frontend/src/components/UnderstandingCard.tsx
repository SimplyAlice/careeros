import React from 'react';
import type { PlanRead } from '../types/planning';
import { formatCurrency } from '../utils/itineraryBuilder';
import { IconMapPin, IconCalendar, IconUsers, IconWallet, IconInfo, IconSparkles } from './Icons';

interface UnderstandingCardProps {
  plan: PlanRead;
  budgetMax: number | null;
}

export const UnderstandingCard: React.FC<UnderstandingCardProps> = ({ plan, budgetMax }) => {
  const u = plan.understanding;

  // Derive human occasion headline
  const occasionMap: Record<string, string> = {
    date: 'Date with Partner',
    birthday: 'Birthday Celebration',
    celebration: 'Celebration',
    friends: 'Outing with Friends',
    casual_hangout: 'Casual Hangout',
    family: 'Family Outing',
    solo: 'Solo Exploration',
  };
  const occasionTitle = u?.occasion
    ? occasionMap[u.occasion] || u.occasion
    : u?.time_window
    ? `Built around your ${u.time_window}`
    : 'Built around your day';

  // Group size & relationship
  const groupSize = u?.people_count ?? plan.context?.group_size ?? 1;
  const relContext = u?.relationship_context;
  let groupSummary = groupSize > 1 ? `${groupSize} people` : '1 person';
  if (relContext && groupSize === 2) {
    if (['partner', 'boyfriend', 'girlfriend', 'couple'].includes(relContext)) {
      groupSummary = '2 people · Partner';
    }
  } else if (relContext === 'friends') {
    groupSummary = groupSize > 1 ? `${groupSize} friends` : 'Friends';
  }

  // Timing
  const dateSpec = u?.date_spec;
  const timeWindow = u?.time_window;
  let timeSummary = 'Flexible timing';
  if (dateSpec && timeWindow) {
    timeSummary = `${dateSpec} · ${timeWindow.charAt(0).toUpperCase() + timeWindow.slice(1)}`;
  } else if (dateSpec) {
    timeSummary = dateSpec;
  } else if (timeWindow) {
    timeSummary = timeWindow.charAt(0).toUpperCase() + timeWindow.slice(1);
  }

  // Location
  const location = u?.location || plan.context?.location || 'Cape Town';
  const locationIsDefault = u ? u.location_is_inferred : false;

  // Budget
  let budgetSummary = 'Flexible budget';
  const budgetVal = u?.budget_amount ? Number(u.budget_amount) : budgetMax;
  if (budgetVal !== null && budgetVal > 0) {
    if (u?.budget_kind === 'approximate') {
      budgetSummary = `Around ${formatCurrency(budgetVal)}`;
    } else {
      budgetSummary = `Under ${formatCurrency(budgetVal)}`;
    }
    if (groupSize > 1) {
      const perPerson = Math.round(budgetVal / groupSize);
      budgetSummary += ` (~${formatCurrency(perPerson)}/person)`;
    }
  } else if (u?.budget_kind === 'preference') {
    budgetSummary = 'Budget-conscious';
  }

  // Desired qualities & Atmosphere (extracted verbatim from user intention)
  const desiredVibeItems: string[] = [];

  // 1. Semantic descriptors from intent (M11)
  if (u?.semantic_descriptors && u.semantic_descriptors.length > 0) {
    for (const desc of u.semantic_descriptors) {
      const capitalized = desc.charAt(0).toUpperCase() + desc.slice(1);
      desiredVibeItems.push(`${capitalized} atmosphere`);
    }
  }

  // 2. Structured preferences
  if (u?.preferences && u.preferences.length > 0) {
    for (const pref of u.preferences) {
      if (pref === 'casual') desiredVibeItems.push('Relaxed, casual vibe');
      else if (pref === 'nice') desiredVibeItems.push('Pleasant, inviting setting');
      else if (pref === 'romantic') desiredVibeItems.push('Intimate & atmospheric');
      else if (pref === 'food_focused') desiredVibeItems.push('Food-forward with great dining');
      else if (pref === 'aesthetic') desiredVibeItems.push('Scenic, visually captivating');
      else if (pref === 'outdoors') desiredVibeItems.push('Open-air & outdoor elements');
      else if (pref === 'cultural') desiredVibeItems.push('Local culture & craft');
      else desiredVibeItems.push(pref.replace(/_/g, ' '));
    }
  }

  // 3. Fallback only if no descriptors or preferences exist
  if (desiredVibeItems.length === 0) {
    if (u?.occasion === 'birthday') desiredVibeItems.push('Celebratory dining with group-friendly seating');
    else if (u?.occasion === 'date') desiredVibeItems.push('Thoughtful, memorable date experience');
    else desiredVibeItems.push('Balanced local spots matching your request');
  }

  // Constraints & Boundaries
  const boundaryItems: string[] = [];

  // Setting and Weather context (M11)
  if (u?.weather_context === 'raining' || u?.setting_preference === 'indoor') {
    boundaryItems.push('Sheltered indoor activities (weather-guarded)');
  }

  // Exclusions (M11)
  if (u?.exclusions && u.exclusions.length > 0) {
    for (const excl of u.exclusions) {
      if (excl === 'no_alcohol') boundaryItems.push('No alcohol / bars & breweries strictly excluded');
      else if (excl === 'not_too_fancy') boundaryItems.push('Nothing overly formal, stiff, or pretentious');
      else if (excl === 'no_outdoors') boundaryItems.push('Indoor / covered venues only');
      else if (excl === 'no_clubs') boundaryItems.push('No loud clubs or late nightlife');
      else if (excl === 'nothing_expensive') boundaryItems.push('High value, non-expensive dining');
      else boundaryItems.push(`Exclude ${excl.replace(/_/g, ' ')}`);
    }
  }

  if (budgetVal !== null && budgetVal > 0) {
    boundaryItems.push(`Total cost capped at ${formatCurrency(budgetVal)}`);
  }
  if (u?.duration_limit_minutes) {
    boundaryItems.push(`Paced within ~${Math.round(u.duration_limit_minutes / 60)} hours total`);
  }
  boundaryItems.push(`Coherent sequence for ${groupSummary.toLowerCase()}`);

  return (
    <div className="understanding-brief-section">
      <div className="brief-header">
        <div className="brief-badge">
          <IconSparkles size={13} className="brief-badge-icon" />
          <span>WHAT I HEARD IN YOUR REQUEST</span>
        </div>
        <h2 className="brief-title">{occasionTitle}</h2>
      </div>

      {/* Structured Context Metadata Ribbon */}
      <div className="brief-meta-ribbon">
        <div className="meta-ribbon-item">
          <IconUsers size={15} className="ribbon-icon" />
          <span className="ribbon-text">{groupSummary}</span>
        </div>
        <div className="ribbon-divider" />
        <div className="meta-ribbon-item">
          <IconCalendar size={15} className="ribbon-icon" />
          <span className="ribbon-text">{timeSummary}</span>
        </div>
        <div className="ribbon-divider" />
        <div className="meta-ribbon-item">
          <IconMapPin size={15} className="ribbon-icon" />
          <span className="ribbon-text">
            {location}
            {locationIsDefault && <span className="inferred-tag"> (inferred)</span>}
          </span>
        </div>
        <div className="ribbon-divider" />
        <div className="meta-ribbon-item">
          <IconWallet size={15} className="ribbon-icon" />
          <span className="ribbon-text">{budgetSummary}</span>
        </div>
      </div>

      {/* Editorial Synthesis: Two-column focus */}
      <div className="brief-grid">
        <div className="brief-column">
          <div className="brief-column-label">Desired qualities & vibe</div>
          <div className="brief-column-content">
            <ul className="brief-list">
              {desiredVibeItems.map((item, idx) => (
                <li key={idx} className="brief-list-item">
                  <span className="brief-bullet" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="brief-column">
          <div className="brief-column-label">Constraints & boundaries</div>
          <div className="brief-column-content">
            <ul className="brief-list">
              {boundaryItems.map((item, idx) => (
                <li key={idx} className="brief-list-item">
                  <span className="brief-bullet neutral" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Ambiguities / Planner Notes */}
      {u?.ambiguities && u.ambiguities.length > 0 && (
        <div className="brief-notes">
          <IconInfo size={14} className="notes-icon" />
          <div className="notes-content">
            {u.ambiguities.map((note, idx) => (
              <span key={idx} className="note-text">{note}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
