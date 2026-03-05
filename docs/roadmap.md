# Roadmap

## Goal

Turn TwitchClipper into an automated highlight generator.

**Input:**

- streamer or vod link
- (later) chat replay data

**Output:**

- compiled highlight video
- timestamps and metadata (why each moment was chosen)

## Current state (today)

- Clip montage pipeline supports scrape -> filter -> rank -> duration-based selection -> montage
- VOD highlights pipeline supports VOD download/import, chat fetch/import, spike detection, segment ranking, cutting, and montage
- API supports job submission and status (`/jobs/clip-montage`, `/jobs/vod-highlights`, `/jobs`, `/jobs/{job_id}`, `/jobs/run-next`)
- Optional SQLite persistence stores job states and outputs
- Frontend is planned (next major phase)

## Phase 1: Ranking system for existing clips

**Why:**

- improves current feature
- sets up scoring logic that later works for vod segments too

**Deliverables:**

- define a "score" for a clip
- filter duplicates
- pick top N clips
- tests for scoring rules

**Status:** completed

## Phase 2: Job queue and worker

**Why:**

- vod and video processing takes a long time
- jobs make the system feel like a real service

**Deliverables:**

- job model with states
- in memory queue
- worker loop
- job status output

**Status:** completed

## Phase 3: VOD + Chat spike highlight generator

**Why:**

- this is the resume level feature
- converts full stream into highlights

**Deliverables:**

- download a vod
- download chat log for same vod (or import a chat log)
- spike detector (messages per second)
- segment generator (spike -> time window)
- cut segments from vod
- rank segments
- compile montage
- metadata output

**Status:** completed

## Phase 4: Persistence

**Why:**

- job history and results should survive restarts
- makes debugging way easier

**Deliverables:**

- SQLite tables for jobs and outputs
- store job status and final paths

**Status:** completed (optional, env-gated at runtime)

## Phase 5: Frontend app

**Why:**

- make job flows accessible without manual API/CLI usage
- visualize job progress and produced artifacts

**Deliverables (initial):**

- submit `clip_montage` and `vod_highlights` jobs
- poll and display `queued -> running -> done/failed` states
- show key outputs (montage path, selected clips/segments metadata)
