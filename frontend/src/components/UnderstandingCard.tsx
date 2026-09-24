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

  // Occasion label
  const occasionMap: Record<string, string> = {
    date: 'Date with Partner',
    birthday: 'Birthday Celebration',
    celebration: 'Celebration',
    friends: 'Outing with Friends',
    casual_hangout: 'Casual Hangout',
    family: 'Family Outing',
    solo: 'Solo Exploration',
  };
  const occasionTitle = u?.occasion ? occasionMap[u.occasion] || u.occasion : 'Custom Itinerary';

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
  } else if (u?.budget_kind === 'preference') {
    budgetSummary = 'Budget-conscious';
  }

  // Looking for (preferences + occasion highlights)
  const lookingForItems: string[] = [];
  if (u?.preferences && u.preferences.length > 0) {
    for (const pref of u.preferences) {
      if (pref === 'casual') lookingForItems.push('Relaxed, casual vibe');
      else if (pref === 'nice') lookingForItems.push('Pleasant, inviting setting');
      else if (pref === 'romantic') lookingForItems.push('Intimate & atmospheric');
      else if (pref === 'food_focused') lookingForItems.push('Food-forward with great dining');
      else if (pref === 'aesthetic') lookingForItems.push('Scenic, visually captivating');
      else if (pref === 'outdoors') lookingForItems.push('Open-air & outdoor elements');
      else if (pref === 'cultural') lookingForItems.push('Local culture & craft');
      else lookingForItems.push(pref.replace(/_/g, ' '));
    }
  } else {
    if (u?.occasion === 'birthday') lookingForItems.push('Celebratory atmosphere with good food');
    else if (u?.occasion === 'date') lookingForItems.push('Thoughtful, memorable date experience');
    else lookingForItems.push('Balanced, well-paced local experience');
  }

  // Keeping in mind (hard exclusions + constraints)
  const keepingInMindItems: string[] = [];
  if (u?.exclusions && u.exclusions.length > 0) {
    for (const excl of u.exclusions) {
      if (excl === 'not_too_fancy') keepingInMindItems.push('Nothing overly formal or stiff');
      else if (excl === 'no_outdoors') keepingInMindItems.push('Sheltered / indoor options only');
      else if (excl === 'no_clubs') keepingInMindItems.push('No loud clubs or nightlife');
      else if (excl === 'nothing_expensive') keepingInMindItems.push('High value, non-expensive');
      else keepingInMindItems.push(`Avoid ${excl.replace(/_/g, ' ')}`);
    }
  }
  if (budgetVal !== null && budgetVal > 0) {
    keepingInMindItems.push(`Total cost capped around ${formatCurrency(budgetVal)}`);
  }
  keepingInMindItems.push(`Tailored sequence for ${groupSummary.toLowerCase()}`);

  return (
    <div className="understanding-brief-section">
      <div className="brief-header">
        <div className="brief-badge">
          <IconSparkles size={13} className="brief-badge-icon" />
          <span>HERE’S WHAT I UNDERSTOOD</span>
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

      {/* Editorial Synthesis: Two-column clean focus */}
      <div className="brief-grid">
        <div className="brief-column">
          <div className="brief-column-label">Looking for</div>
          <div className="brief-column-content">
            <ul className="brief-list">
              {lookingForItems.map((item, idx) => (
                <li key={idx} className="brief-list-item">
                  <span className="brief-bullet" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="brief-column">
          <div className="brief-column-label">Keeping in mind</div>
          <div className="brief-column-content">
            <ul className="brief-list">
              {keepingInMindItems.map((item, idx) => (
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
