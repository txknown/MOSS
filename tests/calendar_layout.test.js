import test from "node:test";
import assert from "node:assert/strict";
import { layoutDay, timelinePercent } from "../web/static/renderers/calendar_layout.js";
import { parseDateOnly, localDateKey, formatWeekRange, formatWeekCardRange, formatTimestamp } from "../web/static/dates.js";

const event = (id, start_time, end_time) => ({ id, start_time, end_time });

test("overnight hours are half-height and events crossing 06:00 use both scales", () => {
  assert.equal(timelinePercent(0), 0);
  assert.equal(timelinePercent(1440), 100);
  const nightHour = timelinePercent(360) - timelinePercent(300);
  const dayHour = timelinePercent(420) - timelinePercent(360);
  assert.ok(Math.abs(dayHour - 2 * nightHour) < 1e-10);
  assert.ok(Math.abs(timelinePercent(390) - timelinePercent(330) - (nightHour + dayHour) / 2) < 1e-10);
  for (let minute = 1; minute <= 1440; minute++) {
    assert.ok(timelinePercent(minute) > timelinePercent(minute - 1));
  }
});

test("overlaps preserve original clock positions without widening or partitioning columns", () => {
  const events = [event("long", "09:00", "12:00"), event("nested", "09:30", "10:00"), event("midnight", "00:00", "00:01")];
  const before = JSON.stringify(events);
  const { timed, untimed } = layoutDay(events);
  assert.equal(untimed.length, 0);
  assert.deepEqual(timed.map(({ start, end }) => [start, end]), [[0, 1], [540, 720], [570, 600]]);
  assert.equal(JSON.stringify(events), before);
});

test("missing or invalid ranges are retained without inventing durations", () => {
  const events = [event("blank", "", ""), event("start", "09:00", ""),
    event("end", "", "12:00"), event("invalid", "25:00", "26:00"),
    event("zero", "09:00", "09:00"), event("backward", "12:00", "10:00")];
  const before = JSON.stringify(events);
  assert.deepEqual(layoutDay(events), { timed: [], untimed: events });
  assert.equal(JSON.stringify(events), before);
});

test("date ranges are ISO and include both years across a year boundary", () => {
  assert.equal(formatWeekRange(parseDateOnly("2026-12-28")), "2026-12-28 – 2027-01-03");
  assert.equal(localDateKey(parseDateOnly("2024-02-29")), "2024-02-29");
  assert.equal(localDateKey(parseDateOnly("0099-01-01")), "0099-01-01");
  for (const invalid of ["0000-01-01", "2026-02-29", "2026-13-01", "2026-04-31", "10/05/2026", "2026-1-1"]) {
    assert.equal(parseDateOnly(invalid), null);
  }
});

test("legacy metadata timestamps are formatted without timezone or content reinterpretation", () => {
  assert.equal(formatTimestamp("October 5, 2026, 18:05"), "2026-10-05 18:05");
  assert.equal(formatTimestamp("2026-10-05T18:05:30-05:00"), "2026-10-05 18:05:30-05:00");
  assert.equal(formatTimestamp("2026-10-05"), "2026-10-05");
  assert.equal(formatTimestamp("Unknown timestamp"), "Unknown timestamp");
});

test("week cards use abbreviated months and include both years when needed", () => {
  assert.equal(formatWeekCardRange(parseDateOnly("2026-10-05")), "2026: Oct 5–Oct 11");
  assert.equal(formatWeekCardRange(parseDateOnly("2026-12-28")), "2026: Dec 28 – 2027: Jan 3");
});
