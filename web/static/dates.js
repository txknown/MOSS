"use strict";

export function parseDateOnly(value) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match || Number(match[1]) < 1) return null;
  const date = new Date(0);
  date.setHours(0, 0, 0, 0);
  date.setFullYear(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  if (date.getFullYear() !== Number(match[1]) || date.getMonth() !== Number(match[2]) - 1 || date.getDate() !== Number(match[3])) return null;
  return date;
}

export function localDateKey(date) {
  return `${String(date.getFullYear()).padStart(4, "0")}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function formatWeekRange(startDate) {
  if (!startDate) return "Week";
  const endDate = new Date(startDate);
  endDate.setDate(endDate.getDate() + 6);
  return `${localDateKey(startDate)} – ${localDateKey(endDate)}`;
}

// Format date metadata only; never scan or rewrite user titles or body text.
export function formatTimestamp(value) {
  const text = String(value || "");
  if (/^\d{4}-\d{2}-\d{2}(?:T|$)/.test(text)) return text.replace("T", " ");
  const match = text.match(/^(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4})(.*)$/);
  if (!match) return text;
  const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  return `${match[3]}-${String(months.indexOf(match[1]) + 1).padStart(2, "0")}-${match[2].padStart(2, "0")}${match[4].replace(/^,\s*/, " ")}`;
}

export function formatWeekCardRange(startDate) {
  if (!startDate) return "Week";
  const end = new Date(startDate);
  end.setDate(end.getDate() + 6);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const label = date => `${months[date.getMonth()]} ${date.getDate()}`;
  return startDate.getFullYear() === end.getFullYear()
    ? `${startDate.getFullYear()}: ${label(startDate)}–${label(end)}`
    : `${startDate.getFullYear()}: ${label(startDate)} – ${end.getFullYear()}: ${label(end)}`;
}
