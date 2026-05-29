import { useEffect, useMemo, useRef, useState } from "react";
import Papa from "papaparse";
import {
  Activity,
  BarChart3,
  Bot,
  ChevronLeft,
  ChevronRight,
  Database,
  FileText,
  Filter,
  Heart,
  Lightbulb,
  MessageSquareText,
  Copy,
  Mic,
  RefreshCcw,
  Search,
  Send,
  SlidersHorizontal,
  Sparkles,
  ThumbsUp,
  Table2,
  TrendingUp,
  Volume2,
  VolumeX,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Label,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import DashboardCanvas from "./components/DashboardCanvas.jsx";
import ReportCanvas from "./components/ReportCanvas.jsx";
import DashboardControlPanel from "./components/DashboardControlPanel.jsx";
import ReportHeader from "./components/ReportHeader.jsx";
import SettingsPanel from "./components/SettingsPanel.jsx";
import StoryDrivenDashboard from "./components/StoryDrivenDashboard.jsx";
import { buildDefaultWidgets } from "./lib/defaultWidgets.js";
import { applyStatefulMutations } from "./lib/statefulMutations.js";
import {
  buildActiveContext,
  DEFAULT_WIDGET_SETTINGS,
  VOICE_TO_SPEAKER,
} from "./lib/activeContext.js";
import {
  DEFAULT_DASHBOARD_STATE,
  orchestrateLLM,
  themeClassName,
} from "./lib/dashboardOrchestrator.js";
import { DEMO_REGENERATE_SCENARIOS } from "./lib/demoDashboardScenarios.js";
import { buildShareUrl } from "./lib/documentModel.js";
import { buildExecutiveNarrative } from "./lib/reportData.js";
import { regenerateStory } from "./lib/settingsApi.js";
import {
  getThemeFilterOptions,
  rowMatchesSentimentFilter,
  rowMatchesThemeFilter,
  SENTIMENT_FILTER_OPTIONS,
} from "./lib/filterHelpers.js";
import { chartCategoryLabel } from "./lib/fieldLabels.js";
import { playTtsBlob, prepareTextForTts } from "./lib/ttsPlayback.js";

const REQUIRED_CSV_FIELDS = [
  "SUBMISSION_ID",
  "QUESTION_TEXT",
  "ANSWER_TEXT",
  "WORKSHOP_CODE",
  "SCHOOL_NAME",
];

const DATASET_CSV_URL = "/api/dataset/csv";

const FIELD_CANDIDATES = {
  region: ["workshop region", "school region", "region", "state", "territory", "area"],
  workshop: [
    "workshop topic",
    "workshop name",
    "workshop code",
    "workshop",
    "session",
    "module",
    "event",
  ],
  school: ["school name", "school", "campus", "partner"],
  programType: [
    "program type",
    "workshop topic",
    "school agreement stage",
    "agreement stage",
    "program",
    "stream",
    "type",
  ],
  date: ["workshop date", "submitted on", "date", "session date", "created"],
  participantGroup: [
    "year level",
    "participant group",
    "gender",
    "cohort",
    "group",
  ],
  attendees: [
    "number of students",
    "students attended",
    "attendees",
    "attendance",
    "participants",
  ],
  feedback: [
    "answer text",
    "workshop gems",
    "anything else to note",
    "feedback",
    "response",
    "responses",
    "comment",
  ],
  preScore: ["pre", "before", "baseline"],
  postScore: ["post", "after", "follow up", "follow-up"],
  outcome: ["answer value", "facilitator workshop rating", "outcome", "score"],
  sentiment: ["answer text", "sentiment", "mood", "rating"],
  theme: ["workshop topic", "question text", "theme", "topic", "keyword", "category"],
};

const FILTER_FIELDS = [
  ["region", "Region"],
  ["workshop", "Workshop"],
  ["school", "School"],
  ["programType", "Program Type"],
  ["participantGroup", "Participant Group"],
  ["feedbackTheme", "Feedback Theme"],
  ["sentimentFilter", "Sentiment"],
];

const CHART_COLORS = ["#000000", "#87BAE5", "#FFD100", "#6A8FB3", "#4A4A4A"];
const DEFAULT_WIDGET_IDS = new Set([
  "widget-rev-ytd",
  "widget-user-growth",
  "widget-morning-briefing",
]);
const CONTROL_MIN_WIDTH = 240;
const CONTROL_MAX_WIDTH = 420;
const CONTROL_COLLAPSED_WIDTH = 76;
const CONTROL_DEFAULT_WIDTH = 300;
const CHAT_MIN_WIDTH = 280;
const CHAT_MAX_WIDTH = 480;
const CHAT_DEFAULT_WIDTH = 340;
const CHAT_COLLAPSED_WIDTH = 76;
const THEME_KEYWORDS = [
  ["Confidence", ["confidence", "confident", "speak up", "speaking"]],
  ["Stress management", ["stress", "pressure", "breathing", "calm"]],
  ["Self-awareness", ["strength", "self", "identify", "personal"]],
  ["Connection", ["alone", "peer", "others", "friend", "safe space"]],
  ["Optimism", ["optimism", "goal", "future", "hope"]],
  ["Engagement", ["activity", "interactive", "examples", "mentor"]],
  ["Follow-up support", ["follow up", "resources", "more time", "reinforce"]],
];

function normalise(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function toNumber(value) {
  const cleaned = String(value ?? "").replace(/[^0-9.-]/g, "").trim();
  if (!cleaned || cleaned === "-" || cleaned === "." || cleaned === "-.") return null;

  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

function getValue(row, field) {
  return field ? row[field] : "";
}

function inferFields(headers) {
  const normalisedHeaders = headers.map((header) => ({
    original: header,
    normalised: normalise(header),
  }));

  return Object.fromEntries(
    Object.entries(FIELD_CANDIDATES).map(([field, candidates]) => {
      const exactMatch = candidates
        .map((candidate) => normalise(candidate))
        .map((candidate) =>
          normalisedHeaders.find(({ normalised: header }) => header === candidate),
        )
        .find(Boolean);
      const fuzzyMatch = candidates
        .map((candidate) => normalise(candidate))
        .map((candidate) =>
          normalisedHeaders.find(({ normalised: header }) =>
            header.includes(candidate),
          ),
        )
        .find(Boolean);

      return [field, (exactMatch || fuzzyMatch)?.original || ""];
    }),
  );
}

function uniqueValues(rows, field) {
  if (!field) return [];

  return [...new Set(rows.map((row) => String(row[field] ?? "").trim()))]
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b));
}

function filterRowsWithFilters(rows, fields, filters) {
  return rows.filter((row) => {
    const matchesFilters = FILTER_FIELDS.every(([field]) => {
      if (field === "feedbackTheme") {
        return rowMatchesThemeFilter(
          row,
          fields,
          filters.feedbackTheme,
          THEME_KEYWORDS,
        );
      }
      if (field === "sentimentFilter") {
        return rowMatchesSentimentFilter(
          row,
          fields,
          filters.sentimentFilter,
          sentimentBucket,
        );
      }
      if (!fields[field] || filters[field] === "All") return true;
      return String(row[fields[field]] || "") === filters[field];
    });

    if (!matchesFilters) return false;

    if (fields.date && (filters.fromDate || filters.toDate)) {
      const rowDate = new Date(row[fields.date]);
      if (Number.isNaN(rowDate.getTime())) return false;
      const rowIso = rowDate.toISOString().slice(0, 10);
      if (filters.fromDate && rowIso < filters.fromDate) return false;
      if (filters.toDate && rowIso > filters.toDate) return false;
    }

    return true;
  });
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function detectQuestionFilters(question, rows, fields, currentFilters) {
  const questionText = normalise(question);
  const nextFilters = { ...currentFilters };
  const applied = [];

  FILTER_FIELDS.forEach(([field, label]) => {
    if (!fields[field]) return;

    const values = uniqueValues(rows, fields[field]);
    const match = values.find((value) => {
      const normalisedValue = normalise(value);
      if (!normalisedValue) return false;
      return questionText.includes(normalisedValue);
    });

    if (match && nextFilters[field] !== match) {
      nextFilters[field] = match;
      applied.push({
        field,
        label,
        value: match,
        displayValue:
          field === "participantGroup" && /^\d+$/.test(match) ? `Year ${match}` : match,
      });
    }
  });

  if (fields.participantGroup && nextFilters.participantGroup === "All") {
    const yearMatch = questionText.match(/\byear\s*([0-9]{1,2})\b/);
    if (yearMatch) {
      const values = uniqueValues(rows, fields.participantGroup);
      const yearValue = values.find((value) =>
        normalise(value).includes(`year ${yearMatch[1]}`) ||
        normalise(value) === yearMatch[1],
      );

      if (yearValue) {
        nextFilters.participantGroup = yearValue;
        applied.push({
          field: "participantGroup",
          label: "Participant group",
          value: yearValue,
          displayValue: `Year ${yearMatch[1]}`,
        });
      }
    }
  }

  return { filters: nextFilters, applied };
}

function buildPendingDashboardCommands(applied, filters) {
  return applied.map((item) => ({
    action: "filter-table",
    targetWidgetId: `filter-${item.field}`,
    value: { field: item.field, value: filters[item.field] },
  }));
}

async function executeDashboardCommand(command, { onApplyFilter }) {
  const response = await fetch("/api/dashboard/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action: command.action,
      targetWidgetId: command.targetWidgetId,
      value: command.value,
    }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Dashboard command failed");
  }
  const payload = await response.json();
  const action = payload.action || command.action;
  const targetWidgetId = payload.targetWidgetId ?? command.targetWidgetId;
  const value = payload.value ?? command.value;

  if (action === "filter-table" && value?.field && onApplyFilter) {
    onApplyFilter(value.field, value.value);
  } else if (
    action === "focus-widget" ||
    action === "switch-tab" ||
    action === "scroll-to"
  ) {
    if (targetWidgetId) {
      document.getElementById(targetWidgetId)?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }
}

async function sendChatMessage({
  text,
  useSpeaker,
  sessionId,
  activeFilters,
  aggregates,
  evidenceRows,
  availableFields,
  pendingDashboardCommands,
  hasFilterIntent,
}) {
  const response = await fetch("/api/chat/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      useSpeaker,
      session_id: sessionId,
      activeFilters,
      aggregates,
      evidenceRows,
      availableFields,
      pendingDashboardCommands,
    }),
  });

  if (!response.ok) {
    throw new Error("Chat API unavailable");
  }

  let data = await response.json();

  if (data.source !== "langchain" && text && !hasFilterIntent) {
    try {
      const gemma = await requestGemmaAsk(text, sessionId);
      data = {
        ...data,
        botReply: gemma.answer,
        source: "langchain",
      };
    } catch {
      // keep insights reply
    }
  }

  return data;
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-AU").format(Math.round(value || 0));
}

function formatDecimal(value) {
  return Number.isFinite(value) ? value.toFixed(2) : "0.00";
}

function formatSignedDecimal(value) {
  if (!Number.isFinite(value)) return "No valid outcome score data";
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatDecimal(value)}`;
}

function formatOutcomeScore(value) {
  return Number.isFinite(value) ? value.toFixed(2) : "No valid outcome score data";
}

function average(values) {
  const cleanValues = values.filter((value) => Number.isFinite(value));
  if (!cleanValues.length) return null;
  return cleanValues.reduce((total, value) => total + value, 0) / cleanValues.length;
}

function getOutcomeFormula(fields) {
  if (fields.preScore && fields.postScore) {
    return {
      label: "Outcome Score = Average(Post Program Score - Pre Program Score)",
      shortLabel: "Average pre/post uplift",
      sourceColumns: [fields.preScore, fields.postScore],
      type: "prePost",
      valueLabel: "Average Outcome Score",
    };
  }

  if (fields.outcome) {
    return {
      label: `Outcome Score = Average(${fields.outcome})`,
      shortLabel: "Average numeric outcome value",
      sourceColumns: [fields.outcome],
      type: "outcome",
      valueLabel: "Average Outcome Score",
    };
  }

  if (fields.sentiment) {
    return {
      label: `Outcome Score = Average(sentiment derived from ${fields.sentiment})`,
      shortLabel: "Average sentiment-derived score",
      sourceColumns: [fields.sentiment],
      type: "sentiment",
      valueLabel: "Sentiment-Derived Outcome Score",
    };
  }

  return {
    label: "No outcome-related CSV column was detected.",
    shortLabel: "No valid outcome score data",
    sourceColumns: [],
    type: "none",
    valueLabel: "Average Outcome Score",
  };
}

function getRowOutcomeValue(row, fields) {
  const pre = toNumber(getValue(row, fields.preScore));
  const post = toNumber(getValue(row, fields.postScore));

  if (pre !== null && post !== null) return post - pre;

  const outcome = toNumber(getValue(row, fields.outcome));
  if (outcome !== null) return outcome;

  if (!fields.outcome && fields.sentiment) {
    const sentiment = sentimentScore(getValue(row, fields.sentiment));
    return sentiment > 0 ? sentiment : null;
  }

  return null;
}

function buildOutcomeStats(rows, fields) {
  const formula = getOutcomeFormula(fields);
  const valid = rows
    .map((row) => ({ row, value: getRowOutcomeValue(row, fields) }))
    .filter((item) => Number.isFinite(item.value));
  const averageValue = average(valid.map((item) => item.value));

  return {
    average: averageValue,
    displayValue: formatOutcomeScore(averageValue),
    evidenceRows: valid.slice(0, 8).map((item) => item.row),
    excludedRows: Math.max(rows.length - valid.length, 0),
    formulaLabel: formula.label,
    hasValidData: Number.isFinite(averageValue),
    shortLabel: formula.shortLabel,
    sourceColumns: formula.sourceColumns,
    type: formula.type,
    validRows: valid.length,
    valueLabel: formula.valueLabel,
  };
}

function sentimentScore(value) {
  const numeric = toNumber(value);
  if (numeric !== null) return numeric;

  const text = normalise(value);
  if (text.includes("very positive")) return 5;
  if (text.includes("strongly agree")) return 5;
  if (text.includes("positive")) return 4;
  if (text.includes("agree")) return 4;
  if (text.includes("neutral")) return 3;
  if (text.includes("disagree")) return 2;
  if (text.includes("negative")) return 2;
  return 0;
}

function sentimentBucket(row, fields) {
  const answer = normalise(getValue(row, fields.sentiment) || getValue(row, fields.feedback));
  const score = sentimentScore(getValue(row, fields.sentiment));

  if (
    score >= 4 ||
    answer.includes("agree") ||
    answer.includes("confident") ||
    answer.includes("help") ||
    answer.includes("valued") ||
    answer.includes("safe")
  ) {
    return "Positive";
  }

  if (
    score > 0 && score <= 2 ||
    answer.includes("disagree") ||
    answer.includes("negative") ||
    answer.includes("more time") ||
    answer.includes("follow up") ||
    answer.includes("support")
  ) {
    return "Needs attention";
  }

  return "Neutral";
}

function sentimentBreakdown(rows, fields) {
  const counts = rows.reduce(
    (current, row) => {
      const bucket = sentimentBucket(row, fields);
      current[bucket] += 1;
      return current;
    },
    { Positive: 0, Neutral: 0, "Needs attention": 0 },
  );

  return Object.entries(counts).map(([name, value]) => ({ name, value }));
}

function extractFeedbackText(row, fields) {
  return [
    getValue(row, fields.feedback),
    row.WORKSHOP_GEMS,
    row.ANYTHING_ELSE_TO_NOTE,
    row.QUESTION_TEXT,
  ]
    .filter(Boolean)
    .join(" ");
}

function inferredThemes(rows, fields, limit = 7) {
  const themeCounts = new Map();

  rows.forEach((row) => {
    const text = normalise(extractFeedbackText(row, fields));
    THEME_KEYWORDS.forEach(([theme, keywords]) => {
      if (keywords.some((keyword) => text.includes(normalise(keyword)))) {
        themeCounts.set(theme, (themeCounts.get(theme) || 0) + 1);
      }
    });
  });

  return [...themeCounts.entries()]
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
}

function warningSignals(rows, fields) {
  const signals = [];
  const lowOutcomes = rows.filter((row) => {
    const outcome = getRowOutcomeValue(row, fields);
    return outcome !== null && outcome > 0 && outcome <= 2;
  });
  const attentionRows = rows.filter((row) => sentimentBucket(row, fields) === "Needs attention");
  const compromisedRows = rows.filter(
    (row) =>
      normalise(row.WAS_WORKSHOP_COMPROMISED).includes("true") ||
      normalise(row.DID_WORKSHOP_DEVIATE).includes("true"),
  );

  if (lowOutcomes.length) {
    signals.push(`${formatNumber(lowOutcomes.length)} rows have lower outcome scores.`);
  }
  if (attentionRows.length) {
    signals.push(`${formatNumber(attentionRows.length)} feedback rows suggest follow-up or extra support.`);
  }
  if (compromisedRows.length) {
    signals.push(`${formatNumber(compromisedRows.length)} workshop records mention compromise or deviation.`);
  }

  return signals.length ? signals : ["No major early warning signal is visible in the current filter view."];
}

function groupAverage(rows, groupField, fields, limit = 8) {
  if (!groupField) return [];

  const grouped = new Map();
  rows.forEach((row) => {
    const outcomeValue = getRowOutcomeValue(row, fields);
    if (outcomeValue === null) return;

    const name = String(row[groupField] || "Unknown").trim() || "Unknown";
    const current = grouped.get(name) || {
      name,
      count: 0,
      sourceRows: [],
      total: 0,
    };
    current.count += 1;
    current.total += outcomeValue;
    if (current.sourceRows.length < 4) current.sourceRows.push(row.__rowNumber);
    grouped.set(name, current);
  });

  return [...grouped.values()]
    .map((item) => ({
      ...item,
      value: Number((item.total / item.count).toFixed(2)),
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
}

function groupCount(rows, groupField, limit = 8) {
  if (!groupField) return [];

  const grouped = new Map();
  rows.forEach((row) => {
    const name = String(row[groupField] || "Unknown").trim() || "Unknown";
    grouped.set(name, (grouped.get(name) || 0) + 1);
  });

  return [...grouped.entries()]
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
}

function sentimentTrend(rows, fields) {
  if (!fields.date || !fields.sentiment) return [];

  const grouped = new Map();
  rows.forEach((row) => {
    const date = new Date(row[fields.date]);
    if (Number.isNaN(date.getTime())) return;

    const month = date.toLocaleDateString("en-AU", {
      month: "short",
      year: "2-digit",
    });
    const score = sentimentScore(row[fields.sentiment]);
    if (!score) return;

    const current = grouped.get(month) || { name: month, count: 0, total: 0 };
    current.count += 1;
    current.total += score;
    grouped.set(month, current);
  });

  return [...grouped.values()].map((item) => ({
    name: item.name,
    value: Number((item.total / item.count).toFixed(2)),
  }));
}

function buildAggregates(rows, fields) {
  const outcome = buildOutcomeStats(rows, fields);
  const attendees = fields.attendees
    ? rows.reduce((total, row) => total + (toNumber(row[fields.attendees]) || 0), 0)
    : rows.length;
  const feedbackRows = fields.feedback
    ? rows.filter((row) => String(row[fields.feedback] || "").trim()).length
    : rows.length;
  const avgPre = average(rows.map((row) => toNumber(getValue(row, fields.preScore))));
  const avgPost = average(rows.map((row) => toNumber(getValue(row, fields.postScore))));

  return {
    rowCount: rows.length,
    attendees,
    feedbackRows,
    avgPre,
    avgPost,
    avgImprovement: outcome.average,
    outcome,
    byRegion: groupAverage(rows, fields.region, fields),
    byWorkshop: groupAverage(rows, fields.workshop, fields),
    byProgram: groupAverage(rows, fields.programType, fields),
    bySchool: groupAverage(rows, fields.school, fields),
    byParticipantGroup: groupAverage(rows, fields.participantGroup, fields),
    byTheme: groupCount(rows, fields.theme),
    inferredThemes: inferredThemes(rows, fields),
    sentimentBreakdown: sentimentBreakdown(rows, fields),
    sentiment: sentimentTrend(rows, fields),
    warningSignals: warningSignals(rows, fields),
  };
}

function createLocalInsight({ aggregates, filters, fields, evidenceRows, question }) {
  const activeFilters = Object.entries(filters)
    .filter(([, value]) => value && value !== "All")
    .map(([key, value]) => `${key}: ${value}`);
  const strongestRegion = aggregates.byRegion[0];
  const strongestWorkshop = aggregates.byWorkshop[0];
  const strongestTheme = aggregates.byTheme[0];
  const filterText = activeFilters.length ? activeFilters.join(", ") : "all records";
  const evidenceLabel = evidenceRows.length
    ? `${evidenceRows.length} visible evidence rows`
    : "the filtered CSV rows";
  const outcome = aggregates.outcome || buildOutcomeStats([], fields);
  const metricLabel =
    outcome.type === "prePost" ? "average uplift" : "average outcome score";
  const metricValueText = formatOutcomeScore(aggregates.avgImprovement);
  const metricEvidenceText = outcome.hasValidData
    ? `${outcome.validRows} valid outcome rows; ${outcome.excludedRows} excluded. Formula: ${outcome.formulaLabel}.`
    : `No valid outcome score data was detected for this filtered view. Formula checked: ${outcome.formulaLabel}`;
  const topEvidenceRow = evidenceRows[0];
  const strongestValue = strongestRegion || strongestWorkshop;

  return {
    answer:
      question?.trim()
        ? `Based on ${filterText}, the dataset points to ${
            strongestRegion?.name || strongestWorkshop?.name || "the current segment"
          } as the best-performing area${
            outcome.hasValidData
              ? `, with an ${metricLabel} of ${formatOutcomeScore(
                  strongestValue?.value ?? aggregates.avgImprovement,
                )}`
              : ""
          }. This answer is grounded in ${formatNumber(
            aggregates.rowCount,
          )} CSV rows and ${evidenceLabel}. ${metricEvidenceText}`
        : `The current view covers ${formatNumber(
            aggregates.rowCount,
          )} CSV rows. ${
            outcome.hasValidData
              ? `The ${metricLabel} is ${metricValueText}`
              : metricValueText
          }, with ${
            strongestRegion
              ? `${strongestRegion.name} leading the region view`
              : "regional comparison unavailable"
          }. ${metricEvidenceText}`,
    summaryBullets: [
      `${formatNumber(aggregates.rowCount)} source rows match the active filters.`,
      outcome.hasValidData
        ? `The ${metricLabel} is ${metricValueText}, using ${formatNumber(
            outcome.validRows,
          )} valid CSV rows.`
        : "No valid outcome score data exists for the active filters.",
      `${formatNumber(outcome.excludedRows)} rows were excluded from Outcome Score because values were missing or invalid.`,
      strongestWorkshop
        ? `${strongestWorkshop.name} is the strongest workshop segment.`
        : "Workshop field was not detected in the CSV.",
      strongestTheme
        ? `${strongestTheme.name} is the most common feedback theme.`
        : "Theme field was not detected in the CSV.",
    ],
    suggestedChart: fields.region ? "Outcome by region" : "Outcome by workshop",
    evidenceReferences: evidenceRows.slice(0, 4).map((row, index) => ({
      id: index + 1,
      href: `#evidence-row-${row.__rowNumber || index + 1}`,
      label:
        getValue(row, fields.feedback) ||
        getValue(row, fields.theme) ||
        getValue(row, fields.workshop) ||
        "CSV evidence row",
    })),
    linkedDataPoints: [
      strongestValue
        ? {
            label: `${strongestValue.name}: ${formatOutcomeScore(strongestValue.value)}`,
            href: "#chart-region",
          }
        : null,
      outcome.hasValidData
        ? {
            label: `${formatNumber(outcome.validRows)} valid outcome rows`,
            href:
              outcome.evidenceRows[0]?.__rowNumber
                ? `#evidence-row-${outcome.evidenceRows[0].__rowNumber}`
                : "#evidence-table",
          }
        : null,
      {
        label: `${formatNumber(aggregates.rowCount)} matching CSV rows`,
        href: topEvidenceRow
          ? `#evidence-row-${topEvidenceRow.__rowNumber || 1}`
          : "#evidence-table",
      },
    ].filter(Boolean),
    followUpQuestions: [
      "Which segment has the strongest improvement?",
      "What themes appear most often?",
      "Which records need follow-up?",
    ],
  };
}

function isValidCsvRow(row) {
  return REQUIRED_CSV_FIELDS.every((field) => String(row[field] ?? "").trim());
}

async function fetchLangchainStatus() {
  try {
    const response = await fetch("/api/langchain/status");
    if (!response.ok) return null;
    const payload = await response.json();
    return payload.data || payload;
  } catch {
    return null;
  }
}

async function fetchDatasetMeta() {
  try {
    const response = await fetch("/api/dataset");
    if (!response.ok) return null;
    const payload = await response.json();
    return payload.data || payload;
  } catch {
    return null;
  }
}

async function requestGemmaAsk(question, sessionId) {
  const response = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    const detail = err.detail;
    throw new Error(
      typeof detail === "string" ? detail : "Gemma ask API unavailable",
    );
  }
  const payload = await response.json();
  const data = payload.data || payload;
  return {
    answer: data.answer,
    source: "langchain",
    charts: data.charts,
    evidenceReferences: [],
    linkedDataPoints: [],
    summaryBullets: [],
    followUpQuestions: [],
  };
}

async function requestInsight(payload, { sessionId = null, hasFilterIntent = false } = {}) {
  const localFallback = (errorMessage) => {
    const local = createLocalInsight({
      ...payload,
      filters: payload.filters || payload.activeFilters,
      fields: payload.fields || payload.availableFields,
    });
    local.source = "local";
    if (errorMessage) local.errorMessage = errorMessage;
    return local;
  };

  let insightResult = null;
  let networkError = null;

  try {
    const response = await fetch("/api/insights", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("Insight backend unavailable");
    const result = await response.json();
    insightResult = result?.answer ? result : result?.data?.answer ? result.data : null;
    if (!insightResult) throw new Error("Unexpected insight response");
  } catch (error) {
    networkError = error;
  }

  if (insightResult?.source === "langchain") {
    return insightResult;
  }

  const question = (payload.question || "").trim();
  const tryGemmaAsk =
    question && !hasFilterIntent && (insightResult?.source !== "error" || networkError);

  if (insightResult?.source === "error") {
    if (tryGemmaAsk) {
      try {
        return await requestGemmaAsk(question, sessionId);
      } catch {
        return insightResult;
      }
    }
    return insightResult;
  }

  if (tryGemmaAsk) {
    try {
      return await requestGemmaAsk(question, sessionId);
    } catch {
      // fall through to insights or local result
    }
  }

  if (insightResult?.answer) {
    return insightResult;
  }

  return localFallback(networkError?.message || "Backend unavailable");
}

async function fetchMlPredictions() {
  try {
    const response = await fetch("/api/predictions");
    if (!response.ok) return null;
    const payload = await response.json();
    return payload.data || payload;
  } catch {
    return null;
  }
}

async function fetchTtsHealth() {
  const response = await fetch("/api/tts/health");
  if (!response.ok) throw new Error("TTS health check failed");
  return response.json();
}

async function speakText(text, speaker = "narrator") {
  const prepared = prepareTextForTts(text);
  if (!prepared) throw new Error("No text to speak");
  const response = await fetch("/api/tts/speak", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: prepared,
      speaker,
      enhance_clarity: true,
    }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const message = payload.detail || payload.message || "TTS request failed";
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return response.blob();
}

function Card({ children, className = "", ...props }) {
  return (
    <section
      className={`rounded-xl border border-black/10 bg-white shadow-sm ${className}`}
      {...props}
    >
      {children}
    </section>
  );
}

function Badge({ children, className = "" }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border border-black/10 px-2.5 py-1 text-xs font-bold ${className}`}
    >
      {children}
    </span>
  );
}

function Button({ children, className = "", ...props }) {
  return (
    <button
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-full border border-black bg-black px-4 py-2 text-sm font-bold text-white transition hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
      type="button"
      {...props}
    >
      {children}
    </button>
  );
}

function EmptyChart({ label }) {
  return (
    <div className="flex h-72 items-center justify-center rounded-lg border border-dashed border-black/20 bg-black/[0.02] p-6 text-center text-sm font-semibold text-black/50">
      {label}
    </div>
  );
}

function KpiCard({ children, icon: Icon, label, value, helper }) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-black/50">
            {label}
          </p>
          <p className="mt-2 font-garage text-3xl font-black leading-none">{value}</p>
        </div>
        <span className="rounded-full bg-[#FFD100] p-2 text-black">
          <Icon size={18} />
        </span>
      </div>
      <p className="mt-3 text-sm text-black/55">{helper}</p>
      {children ? <div className="mt-3">{children}</div> : null}
    </Card>
  );
}

function FilterSelect({ label, value, options, disabled, onChange }) {
  return (
    <label className="grid gap-2 text-sm font-bold text-black/70">
      {label}
      <select
        className="min-h-10 rounded-lg border border-black/10 bg-white px-3 text-sm font-semibold text-black outline-none ring-[#87BAE5] transition focus:ring-2 disabled:bg-black/[0.04] disabled:text-black/35"
        disabled={disabled}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option>All</option>
        {options.map((option) => (
          <option key={option}>{option}</option>
        ))}
      </select>
    </label>
  );
}

function FilterPanel({
  fields,
  filters,
  rows,
  dates,
  themeOptions,
  collapsed,
  width,
  onToggleCollapsed,
  onResizeStart,
  onFilterChange,
  onDateChange,
  onReset,
}) {
  return (
    <aside
      className="print-exclude relative flex h-full min-h-0 flex-col border-r-2 border-black bg-white transition-[width] duration-200"
      id="filter-panel"
      style={{ width: collapsed ? FILTER_COLLAPSED_WIDTH : width }}
    >
      <div className={collapsed ? "flex items-center justify-between gap-3" : "flex items-center justify-between gap-3 px-6 pb-2 pt-5"}>
        <div className={collapsed ? "sr-only" : ""}>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-black/45">
            ImpactLensAI
          </p>
          <h2 className="font-garage text-2xl font-black">Filter / Explore CSV</h2>
        </div>
        <button
          aria-label={collapsed ? "Expand filters" : "Collapse filters"}
          className={`${collapsed ? "m-4 ml-auto" : ""} rounded-full border border-black/10 bg-[#87BAE5] p-2 text-white transition hover:opacity-85`}
          type="button"
          onClick={onToggleCollapsed}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {collapsed ? (
        <div className="flex flex-1 flex-col items-center gap-4 overflow-hidden px-3 py-4">
          <Filter size={22} />
          <p className="rotate-180 text-xs font-black uppercase tracking-[0.18em] text-black/50 [writing-mode:vertical-rl]">
            Filters
          </p>
          <Badge className="bg-[#FFD100] text-black">
            {
              Object.values(filters).filter((value) => value && value !== "All")
                .length
            }
          </Badge>
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto pb-5 pl-6 pr-5">
          <div className="grid gap-4">
            {FILTER_FIELDS.map(([field, label]) => {
              if (field === "feedbackTheme") {
                return (
                  <FilterSelect
                    disabled={!themeOptions.length}
                    key={field}
                    label={label}
                    options={themeOptions}
                    value={filters.feedbackTheme}
                    onChange={(value) => onFilterChange("feedbackTheme", value)}
                  />
                );
              }
              if (field === "sentimentFilter") {
                return (
                  <FilterSelect
                    key={field}
                    label={label}
                    options={SENTIMENT_FILTER_OPTIONS.filter((item) => item !== "All")}
                    value={filters.sentimentFilter}
                    onChange={(value) => onFilterChange("sentimentFilter", value)}
                  />
                );
              }
              return (
                <FilterSelect
                  key={field}
                  disabled={!fields[field]}
                  label={label}
                  options={uniqueValues(rows, fields[field])}
                  value={filters[field]}
                  onChange={(value) => onFilterChange(field, value)}
                />
              );
            })}
          </div>

          <div className="mt-4 grid gap-3">
            <label className="grid gap-2 text-sm font-bold text-black/70">
              Date range — from
              <input
                className="min-h-10 rounded-lg border border-black/10 px-3 text-sm font-semibold outline-none ring-[#87BAE5] transition focus:ring-2 disabled:bg-black/[0.04]"
                disabled={!fields.date}
                max={filters.toDate || dates.max}
                min={dates.min}
                type="date"
                value={filters.fromDate}
                onChange={(event) => onDateChange("fromDate", event.target.value)}
              />
            </label>
            <label className="grid gap-2 text-sm font-bold text-black/70">
              Date range — to
              <input
                className="min-h-10 rounded-lg border border-black/10 px-3 text-sm font-semibold outline-none ring-[#87BAE5] transition focus:ring-2 disabled:bg-black/[0.04]"
                disabled={!fields.date}
                max={dates.max}
                min={filters.fromDate || dates.min}
                type="date"
                value={filters.toDate}
                onChange={(event) => onDateChange("toDate", event.target.value)}
              />
            </label>
          </div>

          <Button className="mt-5 w-full bg-white text-black" onClick={onReset}>
            <RefreshCcw size={16} />
            Reset filters
          </Button>

          <div className="mt-5 rounded-lg bg-black/[0.03] p-3">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-black/45">
              Dataset fields detected
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {Object.entries(fields).map(([key, value]) => (
                <Badge
                  className={value ? "bg-[#FFD100] text-black" : "bg-white text-black/35"}
                  key={key}
                >
                  {key}: {value || "missing"}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      )}
      {!collapsed ? (
        <button
          aria-label="Resize filter panel"
          className="absolute -right-2 top-0 z-20 flex h-full w-4 cursor-col-resize items-center justify-center bg-transparent"
          type="button"
          onPointerDown={onResizeStart}
        >
          <span className="h-16 w-1 rounded-full bg-black/25 transition group-hover:bg-black" />
        </button>
      ) : null}
    </aside>
  );
}

function ChartCard({ title, subtitle, rowCount, children, ...props }) {
  return (
    <Card className="p-4 scroll-mt-24" {...props}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-garage text-2xl font-black">{title}</h3>
          <p className="mt-1 text-sm text-black/55">{subtitle}</p>
        </div>
        <Badge className="bg-black text-white">{formatNumber(rowCount)} rows</Badge>
      </div>
      {children}
    </Card>
  );
}

function ChartTooltip({ valueLabel, categoryLabel = "Category" }) {
  return (
    <Tooltip
      formatter={(value) => [value, valueLabel]}
      labelFormatter={(label) => `${categoryLabel}: ${chartCategoryLabel(label)}`}
    />
  );
}

function InsightPanel({ insight, aggregates, loading }) {
  return (
    <Card className="bg-white p-5 text-[#111827]">
      <div className="flex items-center gap-3">
        <span className="rounded-full bg-[#87BAE5]/25 p-2 text-[#111827]">
          <Sparkles size={18} />
        </span>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#6B7280]">
            Instant insight
          </p>
          <h2 className="font-garage text-3xl font-black">Current filtered view</h2>
        </div>
      </div>
      <p className="mt-5 text-base leading-7 text-[#374151]">
        {loading ? "Analysing the CSV..." : insight.answer}
      </p>
      <div className="mt-5 grid gap-3">
        {insight.summaryBullets.map((bullet) => (
          <div
            className="rounded-lg border border-black/10 bg-black/[0.03] p-3 text-sm font-semibold text-[#111827]"
            key={bullet}
          >
            {bullet}
          </div>
        ))}
      </div>
      <div className="mt-5 rounded-lg border border-black/10 bg-[#F9FAFB] p-4">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#6B7280]">
          Evidence used
        </p>
        <p className="mt-2 text-sm font-semibold text-[#374151]">
          {formatNumber(aggregates.rowCount)} filtered rows,{" "}
          {formatNumber(aggregates.feedbackRows)} feedback responses.
        </p>
        <p className="mt-2 text-sm text-[#374151]">
          Outcome Score: {aggregates.outcome?.formulaLabel || "No formula detected"}.
          {" "}
          {formatNumber(aggregates.outcome?.validRows || 0)} valid rows used,{" "}
          {formatNumber(aggregates.outcome?.excludedRows || 0)} rows excluded.
        </p>
      </div>
    </Card>
  );
}


function MLPredictionsPanel() {
  const [predictions, setPredictions] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMlPredictions()
      .then(setPredictions)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Card className="p-5">
        <p className="text-sm font-semibold text-black/60">Loading ML predictions from backend…</p>
      </Card>
    );
  }

  if (!predictions?.available) {
    return (
      <Card className="p-5">
        <p className="text-sm font-semibold text-black/60">
          {predictions?.reason || "ML predictions are not available yet."}
        </p>
      </Card>
    );
  }

  const charts = predictions.charts || [];
  const predictedChart = charts.find((chart) => chart.id === "ml_predicted_vs_actual");
  const riskChart = charts.find((chart) => chart.id === "ml_risk_probability_by_topic");
  const forecastChart = charts.find((chart) => chart.id === "ml_wellbeing_forecast");

  return (
    <Card className="p-5" id="ml-predictions">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-black/45">
            Traditional ML
          </p>
          <h2 className="font-garage text-3xl font-black">Workshop outcome predictions</h2>
        </div>
        <Badge className="bg-black text-white">
          {predictions.summary?.models_trained || 0} models trained
        </Badge>
      </div>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-black/65">
        scikit-learn models trained on the LifeChanger CSV in the backend — wellbeing regression,
        at-risk classification, sentiment from text, and a wellbeing forecast by term.
      </p>
      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        {predictedChart?.data?.length ? (
          <ChartCard rowCount={predictions.workshop_count} subtitle={predictedChart.description} title={predictedChart.title}>
            <ResponsiveContainer height={288} width="100%">
              <BarChart data={predictedChart.data} margin={{ bottom: 34, left: 18, right: 12, top: 8 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <ChartTooltip valueLabel="Score" />
                <Bar dataKey="actual" fill="#000000" name="Actual" radius={[8, 8, 0, 0]} />
                <Bar dataKey="predicted" fill="#87BAE5" name="Predicted" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        ) : null}
        {riskChart?.data?.length ? (
          <ChartCard rowCount={predictions.workshop_count} subtitle={riskChart.description} title={riskChart.title}>
            <ResponsiveContainer height={288} width="100%">
              <BarChart data={riskChart.data} layout="vertical" margin={{ bottom: 34, left: 24, right: 20, top: 8 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis tick={{ fontSize: 11 }} type="number" />
                <YAxis dataKey="label" tick={{ fontSize: 11 }} type="category" width={120} />
                <ChartTooltip valueLabel="Risk %" />
                <Bar dataKey="value" fill="#FFD100" name="Risk probability" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        ) : null}
        {forecastChart?.data?.length ? (
          <ChartCard rowCount={predictions.workshop_count} subtitle={forecastChart.description} title={forecastChart.title}>
            <ResponsiveContainer height={288} width="100%">
              <LineChart data={forecastChart.data} margin={{ bottom: 34, left: 18, right: 16, top: 8 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <ChartTooltip valueLabel="Wellbeing" />
                <Line connectNulls dataKey="actual" dot={{ r: 4 }} name="Actual" stroke="#000000" strokeWidth={3} type="monotone" />
                <Line connectNulls dataKey="predicted" dot={{ r: 4 }} name="Forecast" stroke="#87BAE5" strokeWidth={3} type="monotone" />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        ) : null}
      </div>
    </Card>
  );
}

function SuccessCriteriaPanel({ aggregates, rows }) {
  const strongestDriver =
    aggregates.byRegion[0] ||
    aggregates.byWorkshop[0] ||
    aggregates.bySchool[0] ||
    aggregates.byParticipantGroup[0];
  const strongestSchool = aggregates.bySchool[0];
  const strongestGroup = aggregates.byParticipantGroup[0];

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-black/45">
            What success looks like
          </p>
          <h2 className="font-garage text-3xl font-black">
            Quant + qualitative impact analysis
          </h2>
        </div>
        <Badge className="bg-[#FFD100] text-black">
          {formatNumber(rows.length)} evidence rows
        </Badge>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-black/10 bg-black/[0.03] p-4">
          <div className="flex items-center gap-2">
            <Heart size={18} />
            <h3 className="font-garage text-xl font-black">Feedback sentiment</h3>
          </div>
          <div className="mt-4 grid gap-2">
            {aggregates.sentimentBreakdown.map((item) => (
              <div className="grid gap-1" key={item.name}>
                <div className="flex justify-between text-sm font-bold">
                  <span>{item.name}</span>
                  <span>{formatNumber(item.value)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-black/10">
                  <div
                    className="h-full rounded-full bg-[#87BAE5]"
                    style={{
                      width: `${aggregates.rowCount ? (item.value / aggregates.rowCount) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-black/10 bg-white p-4">
          <div className="flex items-center gap-2">
            <Lightbulb size={18} />
            <h3 className="font-garage text-xl font-black">Recurring themes</h3>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {(aggregates.inferredThemes.length ? aggregates.inferredThemes : aggregates.byTheme).map(
              (item) => (
                <Badge className="bg-[#FFD100] text-black" key={item.name}>
                  {item.name}: {formatNumber(item.value)}
                </Badge>
              ),
            )}
          </div>
        </div>

        <div className="rounded-xl border border-black/10 bg-black text-white p-4">
          <div className="flex items-center gap-2">
            <TrendingUp size={18} />
            <h3 className="font-garage text-xl font-black">Drivers + risks</h3>
          </div>
          <div className="mt-4 space-y-3 text-sm leading-6 text-white/80">
            <p>
              Strongest condition:{" "}
              <strong className="text-white">
                {strongestDriver
                  ? `${strongestDriver.name} (${formatOutcomeScore(strongestDriver.value)})`
                  : "Not enough data"}
              </strong>
            </p>
            <p>
              Strongest school:{" "}
              <strong className="text-white">
                {strongestSchool
                  ? `${strongestSchool.name} (${formatOutcomeScore(strongestSchool.value)})`
                  : "Not detected"}
              </strong>
            </p>
            <p>
              Strongest participant group:{" "}
              <strong className="text-white">
                {strongestGroup
                  ? `${strongestGroup.name} (${formatOutcomeScore(strongestGroup.value)})`
                  : "Not detected"}
              </strong>
            </p>
            <div className="border-t border-white/15 pt-3">
              {aggregates.warningSignals.map((signal) => (
                <p key={signal}>{signal}</p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

function AudienceReports({ aggregates, fields, rows }) {
  const topRegion = aggregates.byRegion[0];
  const topWorkshop = aggregates.byWorkshop[0];
  const topTheme =
    aggregates.inferredThemes[0] || aggregates.byTheme[0] || { name: "student experience" };
  const quoteRow =
    rows.find((row) => String(getValue(row, fields.feedback) || "").length > 48) || rows[0];
  const quote = getValue(quoteRow, fields.feedback) || extractFeedbackText(quoteRow || {}, fields);
  const outcomeText = aggregates.outcome?.hasValidData
    ? `The average outcome score is ${formatOutcomeScore(
        aggregates.avgImprovement,
      )}, calculated from ${formatNumber(aggregates.outcome.validRows)} valid rows using ${
        aggregates.outcome.sourceColumns.join(", ") || "detected outcome columns"
      }`
    : "No valid outcome score data is available for this filtered view";
  const reports = [
    {
      audience: "Funders",
      title: "Evidence-heavy reach and outcomes",
      body: `${formatNumber(aggregates.attendees)} attendances are represented in this view, across ${formatNumber(
        aggregates.rowCount,
      )} CSV rows. ${outcomeText}, with ${topRegion?.name || "the leading region"} showing the strongest regional result.`,
    },
    {
      audience: "Schools",
      title: "Student experience and practical value",
      body: `Student feedback most often points to ${topTheme.name}. A representative de-identified comment says: "${quote}".`,
    },
    {
      audience: "Board",
      title: "Strategic insight and risk indicators",
      body: `${
        topWorkshop?.name || "The leading workshop"
      } is currently the strongest workshop condition. Key watchpoints: ${aggregates.warningSignals.join(
        " ",
      )}`,
    },
  ];

  return (
    <Card className="p-5">
      <div className="flex items-center gap-3">
        <span className="rounded-full bg-[#FFD100] p-2">
          <FileText size={18} />
        </span>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-black/45">
            Audience-tailored reports
          </p>
          <h2 className="font-garage text-3xl font-black">Reports generated from filtered evidence</h2>
        </div>
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        {reports.map((report) => (
          <article className="rounded-xl border border-black/10 bg-black/[0.03] p-4" key={report.audience}>
            <Badge className="bg-black text-white">{report.audience}</Badge>
            <h3 className="mt-3 font-garage text-xl font-black">{report.title}</h3>
            <p className="mt-3 text-sm leading-6 text-black/65">{report.body}</p>
          </article>
        ))}
      </div>
    </Card>
  );
}

function ImpactNarrative({ aggregates, fields, rows }) {
  const quoteRow =
    rows.find((row) => String(getValue(row, fields.feedback) || "").length > 56) || rows[0];
  const quote = getValue(quoteRow, fields.feedback) || extractFeedbackText(quoteRow || {}, fields);
  const topTheme = aggregates.inferredThemes[0] || aggregates.byTheme[0];
  const topRegion = aggregates.byRegion[0];
  const outcomeText = aggregates.outcome?.hasValidData
    ? formatOutcomeScore(aggregates.avgImprovement)
    : "no valid outcome score data";

  return (
    <Card className="bg-[#FFD100] p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-black/55">
            Impact narrative generator
          </p>
          <h2 className="font-garage text-3xl font-black">Evidence-backed participant story</h2>
        </div>
        <Badge className="bg-white text-black">
          Source row #{quoteRow?.__rowNumber || 1}
        </Badge>
      </div>
      <p className="mt-4 max-w-4xl text-lg font-semibold leading-8 text-black/75">
        Across the current filtered view, the strongest story is about{" "}
        <a className="font-black underline" href="#evidence-table">
          {topTheme?.name || "student experience"}
        </a>
        . The data shows an average outcome score of{" "}
        <a className="font-black underline" href="#chart-region">
          {outcomeText}
        </a>
        {topRegion ? `, with ${topRegion.name} leading the regional comparison` : ""}.
        A representative de-identified comment says, "{quote}". This ties the
        participant voice back to {formatNumber(aggregates.rowCount)} CSV rows in
        the active dashboard view.
      </p>
    </Card>
  );
}

function ChatPanel({
  collapsed,
  dashboardState,
  dashboardWidgets,
  fields,
  filters,
  rows,
  scopedAggregates,
  seedPrompt,
  width,
  onApplyFilters,
  onApplyFilter,
  onApplyMutations,
  onDashboardStateChange,
  onStoryDashboardUpdate,
  onResizeStart,
  onSeedPromptConsumed,
  onToggleCollapsed,
}) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      sender: "bot",
      content:
        "Hi — I'm your impact copilot. Ask anything about the LifeChanger data; I'll remember our conversation in this session. Try follow-ups like “What about workshops?” after your first question.",
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [ttsChecking, setTtsChecking] = useState(true);
  const [ttsAvailable, setTtsAvailable] = useState(false);
  const [ttsMessage, setTtsMessage] = useState("");
  const [speakEnabled, setSpeakEnabled] = useState(false);
  const chatHistoryRef = useRef(null);
  const [speechLoading, setSpeechLoading] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [llmStatus, setLlmStatus] = useState(null);
  const audioRef = useRef(null);
  const sessionIdRef = useRef(
    `dash-${typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Date.now()}`,
  );

  const [selectedDemoId, setSelectedDemoId] = useState(null);

  const speechBusy = speechLoading || speaking;
  const llmModel = llmStatus?.model;
  const llmConfigured = llmStatus?.llm_configured;

  function stopSpeaking() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setSpeaking(false);
    setSpeechLoading(false);
  }

  async function playSpeech(text) {
    if (!ttsAvailable || ttsChecking || !text?.trim()) return;
    const prepared = prepareTextForTts(text);
    if (!prepared) return;
    stopSpeaking();
    setSpeechLoading(true);
    try {
      const blob = await speakText(prepared);
      setSpeechLoading(false);
      setSpeaking(true);
      const audio = await playTtsBlob(blob, {
        playbackRate: 0.98,
        onEnded: () => {
          setSpeaking(false);
          audioRef.current = null;
        },
      });
      audioRef.current = audio;
    } catch {
      setSpeechLoading(false);
      setSpeaking(false);
    }
  }

  function toggleSpeak() {
    setSpeakEnabled((current) => {
      if (current) stopSpeaking();
      return !current;
    });
  }

  useEffect(() => {
    let cancelled = false;
    setTtsChecking(true);
    Promise.all([fetchTtsHealth(), fetchLangchainStatus()])
      .then(([ttsPayload, lcPayload]) => {
        if (cancelled) return;
        setTtsAvailable(Boolean(ttsPayload.enabled));
        setTtsMessage(ttsPayload.message || "");
        if (lcPayload) setLlmStatus(lcPayload);
      })
      .catch(() => {
        if (cancelled) return;
        setTtsAvailable(false);
        setTtsMessage("TTS service unavailable.");
      })
      .finally(() => {
        if (!cancelled) setTtsChecking(false);
      });

    return () => {
      cancelled = true;
      stopSpeaking();
    };
  }, []);

  useEffect(() => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [messages, loading]);

  async function askQuestion(nextQuestion = question, options = {}) {
    const { forceStoryMode = false } = options;
    const trimmedQuestion = (typeof nextQuestion === "string" ? nextQuestion : question).trim();
    if (!trimmedQuestion || loading) return;

    setLoading(true);

    const intent = detectQuestionFilters(trimmedQuestion, rows, fields, filters);
    const scopedRows = filterRowsWithFilters(rows, fields, intent.filters);
    const scopedAggregates = buildAggregates(scopedRows, fields);
    const evidenceRows = scopedRows.slice(0, 8);
    const pendingCommands = buildPendingDashboardCommands(intent.applied, intent.filters);

    if (intent.applied.length) {
      onApplyFilters(intent.filters);
    }

    setMessages((current) => [
      ...current,
      { role: "user", sender: "user", content: trimmedQuestion },
      ...(intent.applied.length
        ? [
            {
              role: "assistant",
              sender: "bot",
              content: `I applied ${intent.applied
                .map((item) => `${item.label}: ${item.displayValue || item.value}`)
                .join(", ")} so the dashboard now matches your question.`,
              filterChange: intent.applied,
            },
          ]
        : []),
    ]);

    try {
      const storyMode =
        forceStoryMode ||
        /\b(story\s+mode|storytelling|executive\s+briefing|listen\s+to\s+insight|regenerate\s+(the\s+)?dashboard)\b/i.test(
          trimmedQuestion,
        );

      const wantsChartOnDashboard =
        /\b(add|show|create|generate|build|make|plot|draw|display|visuali[sz]e)\b/i.test(
          trimmedQuestion,
        ) &&
        /\b(chart|graph|visual|widget|bar|line|pie|kpi)\b/i.test(trimmedQuestion);

      const orchestration = await orchestrateLLM({
        userPrompt: trimmedQuestion,
        currentDashboardState: dashboardState,
        aggregates: scopedAggregates,
        availableFields: fields,
        activeFilters: intent.filters,
        evidenceRows,
        currentDashboardWidgets: dashboardWidgets.map((widget) => ({
          id: widget.id,
          type: widget.type,
          title: widget.title,
        })),
        dynamicWidgetIds: dashboardWidgets.map((widget) => widget.id),
        useSpeaker: speakEnabled,
        storyMode,
        questionMode: !forceStoryMode && !wantsChartOnDashboard,
        sessionId: sessionIdRef.current,
      });

      if (orchestration.storytellingBlocks?.length || orchestration.visualizations?.length) {
        onStoryDashboardUpdate?.(orchestration);
      }

      if (orchestration.dashboardState) {
        onDashboardStateChange(orchestration.dashboardState);
      }

      onApplyMutations(orchestration.mutations || []);
      onApplyMutations(orchestration.dashboardMutations || []);

      for (const command of pendingCommands) {
        try {
          await executeDashboardCommand(command, { onApplyFilter });
        } catch {
          // continue
        }
      }

      const botText = orchestration.botResponseText;
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          sender: "bot",
          content: botText,
          source: orchestration.source,
          summaryBullets: orchestration.summaryBullets || [],
          evidence: orchestration.evidenceReferences || [],
          linkedDataPoints: orchestration.linkedDataPoints || [],
          uiMutations: [
            ...(orchestration.mutations || []),
            ...(orchestration.dashboardMutations || []),
          ],
        },
      ]);
      if (speakEnabled && botText?.trim()) {
        playSpeech(botText).catch(() => {});
      }
    } catch (error) {
      const fallback = createLocalInsight({
        question: trimmedQuestion,
        aggregates: scopedAggregates,
        filters: intent.filters,
        fields,
        evidenceRows,
      });
      fallback.source = "local";
      fallback.errorMessage = error.message;
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          sender: "bot",
          content: fallback.answer,
          evidence: fallback.evidenceReferences || [],
          linkedDataPoints: fallback.linkedDataPoints || [],
          source: "local",
          errorMessage: fallback.errorMessage,
        },
      ]);
    }

    setQuestion("");
    setLoading(false);
  }

  useEffect(() => {
    if (!seedPrompt?.trim() || loading) return;
    void askQuestion(seedPrompt.trim(), { forceStoryMode: true });
    onSeedPromptConsumed?.();
  }, [seedPrompt]); // eslint-disable-line react-hooks/exhaustive-deps

  const suggestions = [
    "Which region is best for Year 8 students?",
    "What feedback themes are most common?",
    "Which workshops need follow-up?",
  ];

  function loadDemoScenario(scenario) {
    setSelectedDemoId(scenario.id);
    setQuestion(scenario.prompt);
  }

  function runLoadedDemoPrompt() {
    askQuestion(question, { forceStoryMode: true });
  }

  function copyMessage(text) {
    if (text?.trim()) navigator.clipboard.writeText(text.trim()).catch(() => {});
  }

  function regenerateFromMessage(messageIndex) {
    const priorUser = [...messages.slice(0, messageIndex)]
      .reverse()
      .find((msg) => msg.role === "user" || msg.sender === "user");
    if (priorUser?.content) askQuestion(priorUser.content);
  }

  return (
    <aside
      className="print-exclude relative flex h-full min-h-0 flex-col border-l border-black/10 bg-[#fafafa] transition-[width] duration-200"
      id="right-chat-pane"
      style={{ width: collapsed ? CHAT_COLLAPSED_WIDTH : width }}
    >
      <div className="flex h-full min-h-0 flex-col" id="seamless-copilot">
      {!collapsed ? (
        <button
          aria-label="Resize chat panel"
          className="absolute -left-2 top-0 z-20 flex h-full w-4 cursor-col-resize items-center justify-center"
          type="button"
          onPointerDown={onResizeStart}
        >
          <span className="h-16 w-1 rounded-full bg-black/15" />
        </button>
      ) : null}
      {collapsed ? (
        <div className="flex h-full flex-col items-center gap-4 overflow-hidden px-3 py-4">
          <button
            aria-label="Expand chat"
            className="rounded-full bg-black p-2 text-white"
            type="button"
            onClick={onToggleCollapsed}
          >
            <Sparkles size={18} />
          </button>
        </div>
      ) : (
        <>
      <div
        ref={chatHistoryRef}
        className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4"
        id="chat-history"
      >
        {messages.map((message, index) => {
          const isUser = message.sender === "user" || message.role === "user";
          return (
          <div
            className={`flex gap-2 ${isUser ? "flex-row-reverse" : "flex-row"}`}
            key={`${message.role}-${index}`}
          >
            {!isUser ? (
              <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#ede9fe] text-[#5b21b6]">
                <Sparkles size={16} />
              </span>
            ) : null}
            <div className={`max-w-[92%] ${isUser ? "text-right" : ""}`}>
            <div
              className={`inline-block rounded-2xl px-4 py-3 text-left text-sm shadow-sm ${
                isUser
                  ? "bg-black text-white"
                  : "border border-black/8 bg-white text-[#1f2937]"
              }`}
            >
            <p className="whitespace-pre-wrap leading-6">{message.content}</p>
            {!isUser && message.summaryBullets?.length ? (
              <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm font-semibold text-[#374151]">
                {message.summaryBullets.map((bullet) => (
                  <li key={bullet}>{bullet}</li>
                ))}
              </ul>
            ) : null}
            {!isUser && (message.uiMutations?.length || message.dashboardCommands?.length) ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {(message.uiMutations || message.dashboardCommands).map((cmd) => (
                  <Badge
                    className="bg-black/[0.06] text-black"
                    key={`${cmd.action}-${cmd.target || cmd.targetWidgetId}`}
                  >
                    {cmd.action}
                    {cmd.target || cmd.targetWidgetId
                      ? ` → ${cmd.target || cmd.targetWidgetId}`
                      : ""}
                  </Badge>
                ))}
              </div>
            ) : null}
            </div>
            {!isUser ? (
              <div className="mt-2 flex flex-wrap items-center gap-1">
                <button
                  aria-label="Copy text"
                  className="rounded-lg p-1.5 text-black/45 hover:bg-black/[0.06] hover:text-black"
                  type="button"
                  onClick={() => copyMessage(message.content)}
                >
                  <Copy size={14} />
                </button>
                <button
                  aria-label="Good response"
                  className="rounded-lg p-1.5 text-black/45 hover:bg-black/[0.06] hover:text-black"
                  type="button"
                >
                  <ThumbsUp size={14} />
                </button>
                <button
                  aria-label="Regenerate"
                  className="rounded-lg p-1.5 text-black/45 hover:bg-black/[0.06] hover:text-black"
                  type="button"
                  onClick={() => regenerateFromMessage(index)}
                >
                  <RefreshCcw size={14} />
                </button>
                <button
                  aria-label="Read aloud"
                  className="rounded-lg p-1.5 text-black/45 hover:bg-black/[0.06] hover:text-black disabled:opacity-40"
                  disabled={!ttsAvailable || speechBusy}
                  type="button"
                  onClick={() => playSpeech(message.content)}
                >
                  <Volume2 size={14} />
                </button>
              </div>
            ) : null}
            {message.errorMessage && message.source === "error" ? (
              <p className="mt-2 rounded-lg bg-red-50 px-2 py-1 text-xs font-semibold text-red-800">
                {message.errorMessage}
              </p>
            ) : null}
            {message.filterChange?.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {message.filterChange.map((item) => (
                  <Badge className="bg-[#87BAE5] text-white" key={item.field}>
                    {item.label}: {item.displayValue || item.value}
                  </Badge>
                ))}
              </div>
            ) : null}
            {message.linkedDataPoints?.length ? (
              <div className="mt-3 border-t border-black/10 pt-2">
                <p className="text-xs font-bold uppercase text-black/45">
                  Linked data points
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {message.linkedDataPoints.map((point) => (
                    <a
                      className="rounded-full bg-[#FFD100] px-2.5 py-1 text-xs font-bold text-black underline-offset-2 hover:underline"
                      href={point.href}
                      key={point.label}
                    >
                      {point.label}
                    </a>
                  ))}
                </div>
              </div>
            ) : null}
            {message.evidence?.length ? (
              <div className="mt-3 border-t border-black/10 pt-2">
                <p className="text-xs font-bold uppercase text-black/45">
                  Evidence used
                </p>
                <div className="mt-2 max-h-[240px] overflow-y-auto rounded-lg bg-black/[0.03] p-2">
                  {message.evidence.map((item) => (
                    <a
                      className="block text-xs leading-5 text-black/60 underline-offset-2 hover:text-black hover:underline"
                      href={item.href}
                      key={item.id}
                    >
                      {item.id}. {item.label}
                    </a>
                  ))}
                </div>
              </div>
            ) : null}
            </div>
          </div>
        );
        })}

        {loading ? (
          <div className="flex gap-2" role="status">
            <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#ede9fe]">
              <Sparkles size={14} className="text-[#5b21b6]" />
            </span>
            <div className="flex items-center gap-1 rounded-2xl border border-black/8 bg-white px-4 py-3">
              <span className="h-2 w-2 animate-pulse rounded-full bg-black/35" />
              <span className="h-2 w-2 animate-pulse rounded-full bg-black/35 [animation-delay:150ms]" />
              <span className="h-2 w-2 animate-pulse rounded-full bg-black/35 [animation-delay:300ms]" />
            </div>
          </div>
        ) : null}
      </div>

      <div className="border-t border-black/5 bg-gradient-to-t from-[#fafafa] to-transparent p-3">
        <details className="mb-2 text-xs">
          <summary className="cursor-pointer font-semibold text-black/45">Demo prompts</summary>
          <div className="mt-2 grid gap-1">
            {DEMO_REGENERATE_SCENARIOS.map((scenario) => (
              <button
                className="rounded-lg px-2 py-1.5 text-left hover:bg-black/[0.04]"
                key={scenario.id}
                type="button"
                onClick={() => loadDemoScenario(scenario)}
              >
                {scenario.label}
              </button>
            ))}
          </div>
        </details>
        <div className="flex items-end gap-2 rounded-full border border-black/10 bg-white px-3 py-2 shadow-md">
          <textarea
            id="ai-prompt-input"
            className="max-h-24 min-h-[24px] min-w-0 flex-1 resize-none border-0 bg-transparent py-1 text-sm outline-none"
            placeholder="Ask your data…"
            rows={1}
            value={question}
            disabled={loading}
            onChange={(event) => {
              setQuestion(event.target.value);
              setSelectedDemoId(null);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                askQuestion(undefined, {
                  forceStoryMode: Boolean(selectedDemoId),
                });
              }
            }}
          />
          <button
            aria-label={speakEnabled ? "Voice on" : "Voice off"}
            className={`rounded-full p-2 ${speakEnabled ? "text-black" : "text-black/35"}`}
            type="button"
            onClick={toggleSpeak}
          >
            <Mic size={18} />
          </button>
          <button
            aria-label="Send"
            className="rounded-full bg-black p-2 text-white disabled:opacity-40"
            disabled={loading || !question.trim()}
            id="send-message"
            type="button"
            onClick={() =>
              askQuestion(undefined, { forceStoryMode: Boolean(selectedDemoId) })
            }
          >
            <Send size={16} />
          </button>
        </div>
      </div>
        </>
      )}
      </div>
    </aside>
  );
}

function EvidenceTable({ rows, fields }) {
  const columns = [
    ...new Set(
      [
        fields.region,
        fields.workshop,
        fields.school,
        fields.programType,
        fields.feedback,
      ].filter(Boolean),
    ),
  ];

  return (
    <Card className="p-4" id="evidence-table">
      <div className="mb-4 flex items-center gap-3">
        <span className="rounded-full bg-[#FFD100] p-2">
          <Table2 size={18} />
        </span>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-black/45">
            Evidence drawer
          </p>
          <h2 className="font-garage text-2xl font-black">CSV rows behind this view</h2>
        </div>
      </div>
      <div className="overflow-hidden rounded-lg border border-black/10">
        <div className="max-h-80 overflow-auto">
          <table className="w-full min-w-[720px] border-collapse text-left text-sm">
            <thead className="sticky top-0 bg-black text-white">
              <tr>
                {columns.map((column) => (
                  <th className="px-3 py-3 font-bold" key={column}>
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 12).map((row, index) => (
                <tr
                  className="border-t border-black/10 scroll-mt-24 target:bg-[#FFD100]/25"
                  id={`evidence-row-${row.__rowNumber || index + 1}`}
                  key={`${row.__rowNumber || index}-${JSON.stringify(row)}`}
                >
                  {columns.map((column) => (
                    <td className="max-w-[280px] px-3 py-3 align-top text-black/70" key={column}>
                      {row[column] || "-"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}

function App() {
  const [rows, setRows] = useState([]);
  const [fields, setFields] = useState({});
  const [loadState, setLoadState] = useState("loading");
  const [loadError, setLoadError] = useState("");
  const [filters, setFilters] = useState({
    region: "All",
    workshop: "All",
    school: "All",
    programType: "All",
    participantGroup: "All",
    feedbackTheme: "All",
    sentimentFilter: "All",
    fromDate: "",
    toDate: "",
  });
  const [controlsCollapsed, setControlsCollapsed] = useState(false);
  const [chatCollapsed, setChatCollapsed] = useState(false);
  const [controlWidth, setControlWidth] = useState(CONTROL_DEFAULT_WIDTH);
  const [chatWidth, setChatWidth] = useState(CHAT_DEFAULT_WIDTH);
  const [dataRefreshKey, setDataRefreshKey] = useState(0);
  const [datasetMeta, setDatasetMeta] = useState(null);
  const [dashboardState, setDashboardState] = useState(DEFAULT_DASHBOARD_STATE);
  const [dashboardWidgets, setDashboardWidgets] = useState([]);
  const [storyDashboard, setStoryDashboard] = useState({
    visualizations: [],
    storytellingBlocks: [],
  });
  const [narrativeSpeechLoading, setNarrativeSpeechLoading] = useState(false);
  const [ttsReady, setTtsReady] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [shareNotice, setShareNotice] = useState("");
  const [chatSeedPrompt, setChatSeedPrompt] = useState("");
  const [reportCopy, setReportCopy] = useState({
    executiveTitle: "Quarterly Executive Briefing",
    headline: "",
    caution: "",
    briefing: "",
  });
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [widgetSettings, setWidgetSettings] = useState(() => ({
    ...DEFAULT_WIDGET_SETTINGS,
  }));

  const activeContext = useMemo(
    () =>
      buildActiveContext({
        dashboardWidgets,
        storyDashboard,
        datasetMeta,
      }),
    [dashboardWidgets, storyDashboard, datasetMeta],
  );

  const chartAppearance = widgetSettings["revenue-viz"];

  useEffect(() => {
    fetchTtsHealth()
      .then((payload) => setTtsReady(Boolean(payload.enabled)))
      .catch(() => setTtsReady(false));
  }, []);

  async function playNarrative(text) {
    if (!text?.trim() || !ttsReady) return;
    const story = widgetSettings["revenue-story"] || {};
    const speaker = VOICE_TO_SPEAKER[story.voiceModel] || "narrator";
    const rate = Math.min(1.1, Math.max(0.9, story.playbackSpeed || 0.98));
    setNarrativeSpeechLoading(true);
    try {
      const blob = await speakText(text, speaker);
      await playTtsBlob(blob, { playbackRate: rate });
    } finally {
      setNarrativeSpeechLoading(false);
    }
  }

  function handleWidgetSettingChange(target, key, value, { mutationType }) {
    setWidgetSettings((current) => ({
      ...current,
      [target]: { ...(current[target] || {}), [key]: value },
    }));

    if (mutationType === "data-mutation" && key === "xAxisInterval") {
      setSettingsLoading(true);
      orchestrateLLM({
        userPrompt: `Re-format the current data using time grouping: ${value}`,
        currentDashboardState: dashboardState,
        aggregates,
        availableFields: fields,
        activeFilters: filters,
        evidenceRows: filteredRows.slice(0, 8),
        currentDashboardWidgets: dashboardWidgets.map((w) => ({
          id: w.id,
          type: w.type,
          title: w.title,
        })),
        dynamicWidgetIds: dashboardWidgets.map((widget) => widget.id),
        storyMode: true,
      })
        .then((result) => {
          if (result.storytellingBlocks?.length || result.visualizations?.length) {
            setStoryDashboard({
              visualizations: result.visualizations || [],
              storytellingBlocks: result.storytellingBlocks || [],
            });
          }
          applyMutations(result.mutations || []);
          applyMutations(result.dashboardMutations || []);
        })
        .catch(() => {})
        .finally(() => setSettingsLoading(false));
    }
  }

  async function handleRegenerateStory(detailLevel) {
    setSettingsLoading(true);
    handleWidgetSettingChange("revenue-story", "detailLevel", detailLevel, {
      mutationType: "data-mutation",
    });
    try {
      const chartConfig =
        storyDashboard.visualizations?.[0]?.chartConfig ||
        dashboardWidgets.find((w) => w.type?.includes("chart")) ||
        null;
      const result = await regenerateStory({
        detailLevel,
        aggregates,
        activeContext,
        chartConfig,
      });
      setDashboardWidgets((current) =>
        current.map((widget) =>
          widget.id === "widget-morning-briefing"
            ? { ...widget, content: result.narrativeText }
            : widget,
        ),
      );
      setStoryDashboard((current) => ({
        ...current,
        storytellingBlocks: (current.storytellingBlocks || []).map((block, index) =>
          index === 0 ? { ...block, narrativeText: result.narrativeText } : block,
        ),
      }));
      setReportCopy((prev) => ({
        ...prev,
        briefing: result.narrativeText || prev.briefing,
      }));
    } catch {
      // keep existing narrative
    } finally {
      setSettingsLoading(false);
    }
  }

  const applyMutations = (mutations) => {
    applyStatefulMutations(mutations, {
      setDashboardState,
      setDashboardWidgets,
      onApplyFilter: updateFilter,
      onClearConfirm: (run) => {
        if (window.confirm("Clear the entire dashboard? This cannot be undone in-session.")) {
          run();
        }
      },
    });
  };

  useEffect(() => {
    fetchDatasetMeta().then((meta) => {
      if (meta) setDatasetMeta(meta);
    });

    Papa.parse(DATASET_CSV_URL, {
      download: true,
      header: true,
      skipEmptyLines: true,
      complete: (result) => {
        const parsedRows = result.data
          .filter(isValidCsvRow)
          .map((row, index) => ({ ...row, __rowNumber: index + 1 }));
        const headers = result.meta.fields || [];

        if (!parsedRows.length) {
          setLoadState("error");
          setLoadError(
            "No valid rows in the backend dataset. Ensure required CSV columns are present.",
          );
          return;
        }

        setRows(parsedRows);
        setFields(inferFields(headers));
        setLoadState("ready");
      },
      error: () => {
        setLoadState("error");
        setLoadError(
          "Could not load dataset from the backend. Start the API on port 5000 (uvicorn main:app).",
        );
      },
    });
  }, [dataRefreshKey]);

  const dates = useMemo(() => {
    if (!fields.date) return { min: "", max: "" };

    const values = rows
      .map((row) => new Date(row[fields.date]))
      .filter((date) => !Number.isNaN(date.getTime()))
      .map((date) => date.toISOString().slice(0, 10))
      .sort();

    return { min: values[0] || "", max: values.at(-1) || "" };
  }, [fields.date, rows]);

  const filteredRows = useMemo(() => {
    return filterRowsWithFilters(rows, fields, filters);
  }, [fields, filters, rows]);

  const aggregates = useMemo(
    () => buildAggregates(filteredRows, fields),
    [filteredRows, fields],
  );

  useEffect(() => {
    if (loadState !== "ready" || !aggregates.rowCount) return;
    setDashboardWidgets((current) => {
      const defaults = buildDefaultWidgets(aggregates);
      if (!current.length) return defaults;
      return current.map((widget) => {
        if (!DEFAULT_WIDGET_IDS.has(widget.id)) return widget;
        const fresh = defaults.find((item) => item.id === widget.id);
        return fresh ? { ...widget, ...fresh } : widget;
      });
    });
  }, [aggregates, loadState]);

  useEffect(() => {
    if (loadState !== "ready") return;
    const narrative = buildExecutiveNarrative({ aggregates, filters, fields });
    const widgetBriefing = dashboardWidgets.find(
      (w) => w.id === "widget-morning-briefing",
    )?.content;
    setReportCopy((prev) => ({
      executiveTitle: prev.executiveTitle || "Quarterly Executive Briefing",
      headline: prev.headline || narrative.headline,
      caution: prev.caution || narrative.caution,
      briefing: prev.briefing || widgetBriefing || "",
    }));
  }, [aggregates, filters, fields, loadState, dashboardWidgets]);

  const instantInsight = useMemo(
    () =>
      createLocalInsight({
        aggregates,
        filters,
        fields,
        evidenceRows: filteredRows.slice(0, 8),
        question: "",
      }),
    [aggregates, fields, filteredRows, filters],
  );

  const themeFilterOptions = useMemo(
    () => getThemeFilterOptions(rows, fields, THEME_KEYWORDS),
    [rows, fields],
  );

  const hasPrePostScores = Boolean(fields.preScore && fields.postScore);
  const outcome = aggregates.outcome;

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function updatePageTitle(nextTitle) {
    setDashboardState((current) => ({
      ...current,
      pageTitle: nextTitle,
    }));
  }

  function resetFilters() {
    setFilters({
      region: "All",
      workshop: "All",
      school: "All",
      programType: "All",
      participantGroup: "All",
      feedbackTheme: "All",
      sentimentFilter: "All",
      fromDate: "",
      toDate: "",
    });
  }

  function applyChatFilters(nextFilters) {
    setFilters(nextFilters);
  }

  function handleShareLink() {
    const url = buildShareUrl(filters);
    navigator.clipboard.writeText(url).then(
      () => setShareNotice("Link copied to clipboard."),
      () => setShareNotice(url),
    );
  }

  function startControlResize(event) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = controlWidth;

    function handlePointerMove(moveEvent) {
      const nextWidth = startWidth + (moveEvent.clientX - startX);
      setControlWidth(clamp(nextWidth, CONTROL_MIN_WIDTH, CONTROL_MAX_WIDTH));
    }

    function handlePointerUp() {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
  }

  function startChatResize(event) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = chatWidth;

    function handlePointerMove(moveEvent) {
      const nextWidth = startWidth + (startX - moveEvent.clientX);
      setChatWidth(clamp(nextWidth, CHAT_MIN_WIDTH, CHAT_MAX_WIDTH));
    }

    function handlePointerUp() {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
  }

  if (loadState === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#FFD100] p-6">
        <Card className="max-w-md p-6 text-center">
          <Database className="mx-auto" size={34} />
          <h1 className="mt-4 font-garage text-4xl font-black">Loading dataset</h1>
          <p className="mt-2 text-black/60">Loading LifeChanger dataset from backend…</p>
        </Card>
      </main>
    );
  }

  if (loadState === "error") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#FFD100] p-6">
        <Card className="max-w-lg p-6 text-center">
          <Search className="mx-auto" size={34} />
          <h1 className="mt-4 font-garage text-4xl font-black">Dataset missing</h1>
          <p className="mt-2 text-black/60">{loadError}</p>
          <p className="mt-4 rounded-lg bg-black/[0.04] p-3 text-sm font-semibold">
            Run the backend: cd backend && uvicorn main:app --port 5000 --reload
          </p>
        </Card>
      </main>
    );
  }

  const mainThemeClass = themeClassName(dashboardState.theme);

  const editLayoutMode = dashboardState.activeLayout === "edit-mode";

  return (
    <main
      className={`three-column-workspace flex h-screen overflow-hidden ${mainThemeClass}`}
    >
      <DashboardControlPanel
        collapsed={controlsCollapsed}
        dashboardState={dashboardState}
        dates={dates}
        editMode={editLayoutMode}
        fields={fields}
        filterFieldList={FILTER_FIELDS}
        filters={filters}
        rows={rows}
        sentimentOptions={SENTIMENT_FILTER_OPTIONS}
        themeOptions={themeFilterOptions}
        width={controlWidth}
        onDateChange={updateFilter}
        onEditModeChange={(checked) =>
          setDashboardState((current) => ({
            ...current,
            activeLayout: checked ? "edit-mode" : "standard",
          }))
        }
        onFilterChange={updateFilter}
        onOpenAdvancedSettings={() => setSettingsOpen(true)}
        onRefreshData={() => {
          setLoadState("loading");
          setDataRefreshKey((key) => key + 1);
        }}
        onResetFilters={resetFilters}
        onResizeStart={startControlResize}
        onShare={handleShareLink}
        onThemeChange={(theme) =>
          setDashboardState((current) => ({ ...current, theme }))
        }
        onToggleCollapsed={() => setControlsCollapsed((current) => !current)}
      />

      <section
        className="min-h-0 min-w-0 flex-1 overflow-y-auto bg-[#f3f2f1]"
        id="main-dashboard"
      >
        <div className="power-bi-canvas" id="report-export-root">
          <div id="main-report-page">
            <ReportHeader
              dates={dates}
              fields={fields}
              filters={filters}
              rows={rows}
              title={dashboardState.pageTitle}
              onDateChange={updateFilter}
              onFilterChange={updateFilter}
              onTitleChange={updatePageTitle}
            />
            {shareNotice ? (
              <p className="border-b border-black/10 bg-white px-5 py-2 text-sm font-semibold text-black/70 print-exclude">
                {shareNotice}
              </p>
            ) : null}

        <div className="grid gap-5 p-5 lg:p-8">
          <SettingsPanel
            activeContext={activeContext}
            dates={dates}
            fields={fields}
            filters={filters}
            open={settingsOpen}
            settingsLoading={settingsLoading}
            widgetSettings={widgetSettings}
            onClose={() => setSettingsOpen(false)}
            onDateChange={updateFilter}
            onRegenerateStory={handleRegenerateStory}
            onSettingChange={handleWidgetSettingChange}
          />

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              helper="CSV records in the current filter context"
              icon={Database}
              label="Rows analysed"
              value={formatNumber(aggregates.rowCount)}
            />
            <KpiCard
              helper="Uses attendee field when detected"
              icon={Activity}
              label="Students attended"
              value={formatNumber(aggregates.attendees)}
            />
            <KpiCard
              helper={
                outcome?.hasValidData
                  ? "Calculated from valid outcome-related CSV rows only. Missing or invalid values are excluded."
                  : "No valid outcome values were found in the current filter context."
              }
              icon={BarChart3}
              label={hasPrePostScores ? "Outcome uplift" : "Average outcome score"}
              value={
                outcome?.hasValidData
                  ? hasPrePostScores
                    ? formatSignedDecimal(aggregates.avgImprovement)
                    : formatOutcomeScore(aggregates.avgImprovement)
                  : "No valid outcome score data"
              }
            >
              <details className="rounded-lg bg-black/[0.03] p-3 text-xs leading-5 text-black/65">
                <summary className="cursor-pointer font-bold text-black">
                  Formula and evidence
                </summary>
                <p className="mt-2">
                  Outcome Score measures participant improvement or program success
                  based on the available CSV outcome fields.
                </p>
                <p className="mt-2 font-semibold text-black/75">
                  {outcome?.formulaLabel || "No formula available"}
                </p>
                <p className="mt-2">
                  Source columns:{" "}
                  <a className="font-bold underline" href="#evidence-table">
                    {outcome?.sourceColumns?.join(", ") || "none detected"}
                  </a>
                </p>
                <p>
                  Valid rows used: {formatNumber(outcome?.validRows || 0)}.
                  Excluded rows: {formatNumber(outcome?.excludedRows || 0)}.
                </p>
              </details>
            </KpiCard>
            <KpiCard
              helper="Rows with feedback evidence"
              icon={MessageSquareText}
              label="Feedback responses"
              value={formatNumber(aggregates.feedbackRows)}
            />
          </div>

          <div className="grid gap-5">
            <InsightPanel
              aggregates={aggregates}
              insight={instantInsight}
              loading={false}
            />
            <div className="grid gap-5">
              <SuccessCriteriaPanel
                aggregates={aggregates}
                rows={filteredRows}
              />
              <MLPredictionsPanel />
              <div className="grid gap-5 xl:grid-cols-2">
                <ChartCard
                  rowCount={aggregates.rowCount}
                  subtitle={
                    hasPrePostScores
                      ? "Compares average participant outcome movement across each region under the current filters."
                      : "Compares the average participant outcome score across each region under the current filters."
                  }
                  title="Average Outcome Score by Region"
                  id="chart-region"
                >
                  {aggregates.byRegion.length ? (
                    <ResponsiveContainer height={288} width="100%">
                      <BarChart
                        data={aggregates.byRegion}
                        margin={{ bottom: 34, left: 18, right: 12, top: 8 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="name" tick={{ fontSize: 11 }}>
                          <Label
                            offset={-22}
                            position="insideBottom"
                            value="Region"
                          />
                        </XAxis>
                        <YAxis tick={{ fontSize: 11 }}>
                          <Label
                            angle={-90}
                            offset={0}
                            position="insideLeft"
                            style={{ textAnchor: "middle" }}
                            value="Average Outcome Score"
                          />
                        </YAxis>
                        <ChartTooltip
                          categoryLabel="Region"
                          valueLabel="Average Outcome Score"
                        />
                        <Bar
                          dataKey="value"
                          name="Average Outcome Score"
                          radius={[8, 8, 0, 0]}
                        >
                          {aggregates.byRegion.map((entry, index) => (
                            <Cell
                              fill={CHART_COLORS[index % CHART_COLORS.length]}
                              key={entry.name}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyChart label="Region field was not detected in the CSV." />
                  )}
                </ChartCard>

                <ChartCard
                  rowCount={aggregates.rowCount}
                  subtitle="Tracks the average sentiment score by month for the currently filtered feedback rows."
                  title="Sentiment Score Trend Over Time"
                  id="chart-sentiment"
                >
                  {aggregates.sentiment.length ? (
                    <ResponsiveContainer height={288} width="100%">
                      <LineChart
                        data={aggregates.sentiment}
                        margin={{ bottom: 34, left: 18, right: 16, top: 8 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="name" tick={{ fontSize: 11 }}>
                          <Label
                            offset={-22}
                            position="insideBottom"
                            value="Date / Month"
                          />
                        </XAxis>
                        <YAxis tick={{ fontSize: 11 }}>
                          <Label
                            angle={-90}
                            offset={0}
                            position="insideLeft"
                            style={{ textAnchor: "middle" }}
                            value="Sentiment Score"
                          />
                        </YAxis>
                        <ChartTooltip
                          categoryLabel="Date"
                          valueLabel="Sentiment Score"
                        />
                        <Line
                          dataKey="value"
                          dot={{ fill: "#000000", r: 4 }}
                          name="Sentiment Score"
                          stroke="#87BAE5"
                          strokeWidth={4}
                          type="monotone"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyChart label="Date and sentiment fields are needed for this trend." />
                  )}
                </ChartCard>
              </div>

              <div className="grid gap-5 xl:grid-cols-2">
                <ChartCard
                  rowCount={aggregates.rowCount}
                  subtitle={
                    hasPrePostScores
                      ? "Compares average participant uplift across workshop types under the current filters."
                      : "Compares the average outcome score across workshop types under the current filters."
                  }
                  title="Average Outcome Score by Workshop Type"
                  id="chart-workshop"
                >
                  {aggregates.byWorkshop.length ? (
                    <ResponsiveContainer height={288} width="100%">
                      <BarChart
                        data={aggregates.byWorkshop}
                        layout="vertical"
                        margin={{ bottom: 34, left: 24, right: 20, top: 8 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                        <XAxis tick={{ fontSize: 11 }} type="number">
                          <Label
                            offset={-22}
                            position="insideBottom"
                            value="Average Outcome Score"
                          />
                        </XAxis>
                        <YAxis
                          dataKey="name"
                          tick={{ fontSize: 11 }}
                          type="category"
                          width={120}
                        >
                          <Label
                            angle={-90}
                            offset={0}
                            position="insideLeft"
                            style={{ textAnchor: "middle" }}
                            value="Workshop Type"
                          />
                        </YAxis>
                        <ChartTooltip
                          categoryLabel="Workshop Type"
                          valueLabel="Average Outcome Score"
                        />
                        <Bar
                          dataKey="value"
                          fill="#FFD100"
                          name="Average Outcome Score"
                          radius={[0, 8, 8, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyChart label="Workshop field was not detected in the CSV." />
                  )}
                </ChartCard>

                <ChartCard
                  rowCount={aggregates.rowCount}
                  subtitle="Shows the number of feedback responses grouped by feedback theme under the current filters."
                  title="Number of Feedback Responses by Theme"
                  id="chart-theme"
                >
                  {aggregates.byTheme.length ? (
                    <ResponsiveContainer height={288} width="100%">
                      <BarChart
                        data={aggregates.byTheme}
                        margin={{ bottom: 34, left: 18, right: 12, top: 8 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="name" tick={{ fontSize: 11 }}>
                          <Label
                            offset={-22}
                            position="insideBottom"
                            value="Feedback Theme"
                          />
                        </XAxis>
                        <YAxis tick={{ fontSize: 11 }}>
                          <Label
                            angle={-90}
                            offset={0}
                            position="insideLeft"
                            style={{ textAnchor: "middle" }}
                            value="Number of Feedback Responses"
                          />
                        </YAxis>
                        <ChartTooltip
                          categoryLabel="Feedback Theme"
                          valueLabel="Number of Feedback Responses"
                        />
                        <Bar
                          dataKey="value"
                          fill="#000000"
                          name="Number of Feedback Responses"
                          radius={[8, 8, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyChart label="Theme field was not detected in the CSV." />
                  )}
                </ChartCard>
              </div>

              <EvidenceTable fields={fields} rows={filteredRows} />
              <AudienceReports
                aggregates={aggregates}
                fields={fields}
                rows={filteredRows}
              />
              <ImpactNarrative
                aggregates={aggregates}
                fields={fields}
                rows={filteredRows}
              />
            </div>
          </div>

          <div className="grid gap-8">
            <ReportCanvas
              aggregates={aggregates}
              dates={dates}
              fields={fields}
              filters={filters}
              reportCopy={reportCopy}
              speechLoading={narrativeSpeechLoading}
              ttsAvailable={ttsReady}
              onPhraseSelect={(prompt) => {
                setChatSeedPrompt(prompt);
                setChatCollapsed(false);
              }}
              onPlayNarrative={playNarrative}
              onReportCopyChange={setReportCopy}
            />
            <Card className="p-5 shadow-sm" id="dynamic-widgets-area">
              <DashboardCanvas
                chartAppearance={chartAppearance}
                speechLoading={narrativeSpeechLoading}
                ttsAvailable={ttsReady}
                widgets={dashboardWidgets}
                onPlayNarrative={playNarrative}
              />
            </Card>
            {storyDashboard.storytellingBlocks?.length ||
            storyDashboard.visualizations?.length ? (
              <StoryDrivenDashboard
                chartAppearance={chartAppearance}
                storytellingBlocks={storyDashboard.storytellingBlocks}
                speechLoading={narrativeSpeechLoading}
                ttsAvailable={ttsReady}
                visualizations={storyDashboard.visualizations}
                onPlayNarrative={playNarrative}
              />
            ) : null}
          </div>
          </div>
        </div>
        </div>
      </section>

      <ChatPanel
        collapsed={chatCollapsed}
        dashboardState={dashboardState}
        dashboardWidgets={dashboardWidgets}
        fields={fields}
        filters={filters}
        rows={rows}
        scopedAggregates={aggregates}
        seedPrompt={chatSeedPrompt}
        width={chatWidth}
        onApplyFilter={updateFilter}
        onApplyFilters={applyChatFilters}
        onApplyMutations={applyMutations}
        onDashboardStateChange={setDashboardState}
        onStoryDashboardUpdate={setStoryDashboard}
        onResizeStart={startChatResize}
        onSeedPromptConsumed={() => setChatSeedPrompt("")}
        onToggleCollapsed={() => setChatCollapsed((current) => !current)}
      />
    </main>
  );
}

export default App;
