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

- CLI pipeline downloads clips and compiles a montage
- API exists but only `/health`
- frontend is planned

## Phase 1: Ranking system for existing clips

**Why:**

- improves current feature
- sets up scoring logic that later works for vod segments too

**Deliverables:**

- define a "score" for a clip
- filter duplicates
- pick top N clips
- tests for scoring rules

## Phase 2: Job queue and worker

**Why:**

- vod and video processing takes a long time
- jobs make the system feel like a real service

**Deliverables:**

- job model with states
- in memory queue
- worker loop
- job status output

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

## Phase 4: Persistence

**Why:**

- job history and results should survive restarts
- makes debugging way easier

**Deliverables:**

- SQLite tables for jobs and outputs
- store job status and final paths
