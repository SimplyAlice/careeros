import React from 'react';
import type { PlanRead } from '../types/planning';
import { formatCurrency } from '../utils/itineraryBuilder';
import { IconMapPin, IconCalendar, IconUsers, IconWallet, IconInfo } from './Icons';

interface UnderstandingCardProps {
  plan: PlanRead;
  budgetMax: number | null;
}

export const UnderstandingCard: React.FC<UnderstandingCardProps> = ({ plan, budgetMax }) => {
  const u = plan.understanding;

  // Occasion / Concept Headline
  const occasionMap: Record<string, string> = {
    date: 'DATE WITH PARTNER',
    birthday: 'BIRTHDAY CELEBRATION',
    celebration: 'SPECIAL CELEBRATION',
    friends: 'OUTING WITH FRIENDS',
    casual_hangout: 'CASUAL HANGOUT',
    family: 'FAMILY OUTING',
    solo: 'SOLO EXPLORATION',
  };

  const occasionKicker = u?.occasion
    ? occasionMap[u.occasion] || u.occasion.toUpperCase()
    : u?.time_window
    ? `${u.time_window.toUpperCase()} FLOW`
    : 'CUSTOM ITINERARY';

  // Group size & relationship
  const groupSize = u?.people_count ?? plan.context?.group_size ?? 1;
  const relContext = u?.relationship_context;
  let groupSummary = groupSize > 1 ? `${groupSize} PEOPLE` : '1 PERSON';
  if (relContext && groupSize === 2) {
    if (['partner', 'boyfriend', 'girlfriend', 'couple'].includes(relContext)) {
      groupSummary = '2 PEOPLE · PARTNER';
    }
  } else if (relContext === 'friends') {
    groupSummary = groupSize > 1 ? `${groupSize} FRIENDS` : 'FRIENDS';
  }

  // Timing
  const dateSpec = u?.date_spec;
  const timeWindow = u?.time_window;
  let timeSummary = 'FLEXIBLE TIMING';
  if (dateSpec && timeWindow) {
    timeSummary = `${dateSpec.toUpperCase()} · ${timeWindow.toUpperCase()}`;
  } else if (dateSpec) {
    timeSummary = dateSpec.toUpperCase();
  } else if (timeWindow) {
    timeSummary = timeWindow.toUpperCase();
  }

  // Location
  const location = (u?.location || plan.context?.location || 'CAPE TOWN').toUpperCase();
  const locationIsDefault = u ? u.location_is_inferred : false;

  // Budget
  let budgetSummary = 'FLEXIBLE BUDGET';
  const budgetVal = u?.budget_amount ? Number(u.budget_amount) : budgetMax;
  if (budgetVal !== null && budgetVal > 0) {
    if (u?.budget_kind === 'approximate') {
      budgetSummary = `AROUND ${formatCurrency(budgetVal)}`;
    } else {
      budgetSummary = `UNDER ${formatCurrency(budgetVal)}`;
    }
    if (groupSize > 1) {
      const perPerson = Math.round(budgetVal / groupSize);
      budgetSummary += ` (~${formatCurrency(perPerson)}/PERSON)`;
    }
  } else if (u?.budget_kind === 'preference') {
    budgetSummary = 'BUDGET-CONSCIOUS';
  }

  // Desired qualities & Atmosphere
  const desiredVibeItems: string[] = [];
  if (u?.semantic_descriptors && u.semantic_descriptors.length > 0) {
    for (const desc of u.semantic_descriptors) {
      desiredVibeItems.push(desc);
    }
  }
  if (u?.preferences && u.preferences.length > 0) {
    for (const pref of u.preferences) {
      if (pref === 'casual') desiredVibeItems.push('Relaxed, casual vibe');
      else if (pref === 'nice') desiredVibeItems.push('Pleasant, inviting setting');
      else if (pref === 'romantic') desiredVibeItems.push('Intimate & atmospheric');
      else if (pref === 'food_focused') desiredVibeItems.push('Food-forward dining');
      else if (pref === 'aesthetic') desiredVibeItems.push('Scenic, visually captivating');
      else if (pref === 'outdoors') desiredVibeItems.push('Open-air elements');
      else if (pref === 'cultural') desiredVibeItems.push('Local craft & culture');
      else desiredVibeItems.push(pref.replace(/_/g, ' '));
    }
  }
  if (desiredVibeItems.length === 0) {
    if (u?.occasion === 'birthday') desiredVibeItems.push('Celebratory dining with group seating');
    else if (u?.occasion === 'date') desiredVibeItems.push('Thoughtful, memorable date setting');
    else desiredVibeItems.push('Balanced local spots matching your request');
  }

  // Boundaries & Hard Exclusions
  const boundaryItems: string[] = [];
  if (u?.weather_context === 'raining' || u?.setting_preference === 'indoor') {
    boundaryItems.push('Sheltered indoor activities (weather-guarded)');
  }
  if (u?.exclusions && u.exclusions.length > 0) {
    for (const excl of u.exclusions) {
      if (excl === 'no_alcohol') boundaryItems.push('No alcohol (bars & pubs strictly excluded)');
      else if (excl === 'not_too_fancy') boundaryItems.push('Nothing overly stiff or formal');
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

  return (
    <section className="editorial-brief-block">
      {/* Editorial Header Bar */}
      <div className="brief-kicker-strip">
        <span className="brief-kicker-badge">{occasionKicker}</span>
        <span className="brief-kicker-meta">EXTRACTED CONTEXT & OBJECTIVES</span>
      </div>

      <h2 className="brief-headline">
        Built around <em>your intention.</em>
      </h2>

      {/* Metadata Ribbon with Crisp Dividers */}
      <div className="brief-metric-strip">
        <div className="metric-strip-item">
          <IconUsers size={14} className="metric-icon" />
          <span className="metric-text">{groupSummary}</span>
        </div>
        <div className="metric-divider" />
        <div className="metric-strip-item">
          <IconCalendar size={14} className="metric-icon" />
          <span className="metric-text">{timeSummary}</span>
        </div>
        <div className="metric-divider" />
        <div className="metric-strip-item">
          <IconMapPin size={14} className="metric-icon" />
          <span className="metric-text">
            {location}
            {locationIsDefault && <span className="inferred-hint"> (INFERRED)</span>}
          </span>
        </div>
        <div className="metric-divider" />
        <div className="metric-strip-item">
          <IconWallet size={14} className="metric-icon" />
          <span className="metric-text">{budgetSummary}</span>
        </div>
      </div>

      {/* Side-by-Side Architectural Split with Crisp Rule */}
      <div className="brief-split-columns">
        <div className="split-column">
          <span className="column-kicker">01 / DESIRED QUALITIES & VIBE</span>
          <ul className="column-manifesto-list">
            {desiredVibeItems.map((item, idx) => (
              <li key={idx} className="manifesto-item">
                <span className="manifesto-bullet" />
                <span className="manifesto-text">{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="split-column">
          <span className="column-kicker">02 / HARD BOUNDARIES & CONSTRAINTS</span>
          <ul className="column-manifesto-list">
            {boundaryItems.map((item, idx) => (
              <li key={idx} className="manifesto-item">
                <span className="manifesto-bullet alert" />
                <span className="manifesto-text">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Ambiguities / Planner Notes */}
      {u?.ambiguities && u.ambiguities.length > 0 && (
        <div className="brief-notes-strip">
          <IconInfo size={14} className="brief-notes-icon" />
          <div className="brief-notes-list">
            {u.ambiguities.map((note, idx) => (
              <span key={idx} className="brief-note-item">{note}</span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
};
