# SLO & SLI Reference – Battleship RL

## 0. Purpose
This document defines the service level objectives (SLOs) and service level indicators (SLIs) that govern the reliability of the Battleship RL training and evaluation stack. It establishes the authoritative objectives and measurement approach across training, environment, and observability components.

The structure is SLO-centric: we describe each SLO, show the governing SLI, reference the underlying signals, and delegate signal-level implementation details to subordinate catalogues. Dashboards, alert rules, and executive governance should start with this document before drilling into `docs/observability_catalogue.md` for per-signal metadata.

## 1. SLO/SLI Overview
An SLO (Service Level Objective) is the quantitative reliability target for a domain, such as “win rate ≥ 60%.” An SLI (Service Level Indicator) is the measurement expression that proves whether the objective is met, for example “wins / total episodes.” The error budget is the allowable amount of unreliability (e.g., the 40% of episodes that may be non-wins within the window) before governance actions are triggered.

Three observability backends are authoritative: Prometheus provides numeric metrics and rate/histogram-based SLIs, Loki captures structured logs for debugging and validation of rare failures, and Tempo stores spans used for latency and interaction SLIs.

The Battleship RL training loop is instrumented at every episode boundary: rewards, win/loss flags, number of steps, placement success, exploration parameters (epsilon, entropy), training signals (loss, gradient norms), and environment timings (action latency, reset latency, env step durations). Telemetry health metrics ensure the collector, exporters, and pipelines remain trustworthy.

## 2. SLO/SLI Domain Index
- **Learning Progress**
  - `SLO-LRN-001: Episode Win Rate`
  - `SLO-LRN-002: Episode Reward Trend`
- **Agent Performance**
  - `SLO-PERF-001: Hit/Miss Accuracy`
  - `SLO-PERF-002: Steps-to-Win Efficiency`
- **Training Stability**
  - `SLO-STAB-001: Loss Stability`
  - `SLO-STAB-002: Gradient Norm Health`
- **Exploration & Policy**
  - `SLO-EXP-001: Epsilon Schedule Health`
  - `SLO-EXP-002: Policy Entropy Range`
- **Latency / Interaction**
  - `SLO-LAT-001: Agent Action Latency`
  - `SLO-LAT-002: Episode Reset Latency`
- **Environment / Engine Integrity**
  - `SLO-ENV-001: Placement Success Rate`
  - `SLO-ENV-002: Invalid Action Rejection Rate`
  - `SLO-ENV-003: Board State Consistency`
  - `SLO-ENV-004: Environment Step Latency`
  - `SLO-ENV-005: Reward Integrity`
- **Observability Pipeline**
  - `SLO-OBS-001: Telemetry Drop Rate`
  - `SLO-OBS-002: Exporter Reliability`
  - `SLO-OBS-003: Collector Queue Pressure`

## 3. Detailed SLO & SLI Definitions

### 3.1 SLO-LRN-001 — Episode Win Rate

**SLO Summary**  
- **Domain:** Learning Progress  
- **ID:** SLO-LRN-001  
- **Objective:** Win rate ≥ 60% over the last 1000 episodes  
- **Window:** Sliding window of the most recent 1000 completed episodes per run  
- **Error Budget:** 40% of episodes may be non-wins in the window  
- **Authoritative Backend:** Prometheus  

**SLI Definition**  
- **Name:** Episode Win Rate SLI  
- **What it measures:** Proportion of episodes that result in an agent victory in the configured window.  
- **Why it matters:** Sustained win rate confirms the policy is improving and remains above the minimum acceptable competency for downstream evaluation.

**SLI Formula (Logical)**
```text
wins / total_episodes over the last 1000 completed episodes
```
Reference Queries
Prometheus:
```promql
sum_over_time(battleship_episode_win{run_id="$run"}[1000episodes])
  /
count_over_time(battleship_episode_win{run_id="$run"}[1000episodes])
```
Related Signals
- `battleship_episode_win` — metric — Prometheus — 0/1 counter per completed episode

Notes
- Use per-run grouping labels (`run_id`, `agent_id`) to avoid mixing experiments; shared dashboards should overlay a baseline comparator.

### 3.2 SLO-LRN-002 — Episode Reward Trend

**SLO Summary**  
- **Domain:** Learning Progress  
- **ID:** SLO-LRN-002  
- **Objective:** Mean episode reward must not drop by >10% between consecutive 500-episode windows and must increase ≥20% during the first 2000 episodes.  
- **Window:** Rolling 500-episode and 2000-episode cohorts evaluated per run.  
- **Error Budget:** At most one consecutive window breach (≥10% drop or <20% initial lift) before intervention.  
- **Authoritative Backend:** Prometheus  

**SLI Definition**  
- **Name:** Episode Reward Trend SLI  
- **What it measures:** Relative change of average episode reward across sequential windows plus cumulative gain during ramp-up.  
- **Why it matters:** Detects regressions where policy reward collapses or stagnates despite continuing training steps.

**SLI Formula (Logical)**
```text
trend = (avg_reward_window_n - avg_reward_window_n-1) / avg_reward_window_n-1
initial_gain = (avg_reward_episodes_1_2000 - avg_reward_episodes_1_500) / avg_reward_episodes_1_500
SLO holds when trend >= -0.10 for all windows and initial_gain >= 0.20
```
Reference Queries
Prometheus:
```promql
avg_over_time(battleship_episode_reward_sum{run_id="$run"}[500episodes])
```
Prometheus (window-to-window comparison via recording rule):
```promql
(trend_reward{run_id="$run"} >= -0.10)
  and
(initial_reward_gain{run_id="$run"} >= 0.20)
```
Related Signals
- `battleship_episode_reward_sum` — metric — Prometheus — Cumulative reward per episode
- `episode_reward_window_avg` — metric — Prometheus — Recording rule storing rolling averages

Notes
- Derive `trend_reward` and `initial_reward_gain` as recording rules so alerting logic remains simple and comparable between runs.

### 3.3 SLO-PERF-001 — Hit/Miss Accuracy

**SLO Summary**  
- **Domain:** Agent Performance  
- **ID:** SLO-PERF-001  
- **Objective:** Hit rate ≥ 45% over the last 1000 episodes.  
- **Window:** Sliding 1000-episode accumulation per run.  
- **Error Budget:** Up to 55% of shots may be misses within the window.  
- **Authoritative Backend:** Prometheus  

**SLI Definition**  
- **Name:** Hit Accuracy SLI  
- **What it measures:** Ratio of hits to total shots (hits + misses) aggregated per window.  
- **Why it matters:** Captures effectiveness of the attack policy independent of reward shaping, highlighting tactical execution quality.

**SLI Formula (Logical)**
```text
hits / (hits + misses) over the last 1000 episodes
```
Reference Queries
Prometheus:
```promql
sum_over_time(env_hits_total{run_id="$run"}[1000episodes])
  /
(sum_over_time(env_hits_total{run_id="$run"}[1000episodes])
 + sum_over_time(env_misses_total{run_id="$run"}[1000episodes]))
```
Related Signals
- `env_hits_total` — metric — Prometheus — Shot results labelled hit
- `env_misses_total` — metric — Prometheus — Shot results labelled miss

Notes
- Ensure misses exclude invalid placements to avoid double-counting with placement SLOs.

### 3.4 SLO-PERF-002 — Steps-to-Win Efficiency

**SLO Summary**  
- **Domain:** Agent Performance  
- **ID:** SLO-PERF-002  
- **Objective:** Average steps to win ≤ 85% of baseline random policy.  
- **Window:** Sliding window of 1000 winning episodes, compared to baseline metric refreshed daily.  
- **Error Budget:** At most 15% slack versus baseline before action.  
- **Authoritative Backend:** Prometheus  

**SLI Definition**  
- **Name:** Steps to Win Efficiency SLI  
- **What it measures:** Ratio of agent steps-to-win vs. recorded baseline (random policy) value.  
- **Why it matters:** Validates sample efficiency improvements and guards against regressions where policies require excessive moves.

**SLI Formula (Logical)**
```text
avg(agent_steps_to_win) / baseline_random_steps_to_win <= 0.85
```
Reference Queries
Prometheus:
```promql
avg_over_time(env_steps_to_win{policy="agent", run_id="$run"}[1000episodes])
  /
max(env_steps_to_win{policy="random_baseline"})
```
Related Signals
- `env_steps_to_win` — metric — Prometheus — Histogram or gauge of steps for winning episodes (label `policy`)
- `baseline_steps_to_win` — metric — Prometheus — Recording rule storing random baseline reference

Notes
- Refresh the baseline metric at least daily or when environment changes; stale baselines invalidate comparisons.

### 3.5 SLO-STAB-001 — Loss Stability

**SLO Summary**  
- **Domain:** Training Stability  
- **ID:** SLO-STAB-001  
- **Objective:** ≤0.5% of loss samples are NaN/Inf and variance stays within configured band.  
- **Window:** Continuous evaluation over 10,000 training steps.  
- **Error Budget:** 0.5% invalid samples and variance band defined per run.  
- **Authoritative Backend:** Prometheus  

**SLI Definition**  
- **Name:** Loss Stability SLI  
- **What it measures:** Combination of loss sample health (finite values) and statistical variance.  
- **Why it matters:** Detects optimizer instability or data path issues that would derail learning.

**SLI Formula (Logical)**
```text
invalid_rate = invalid_loss_samples / total_loss_samples
variance = var(loss_samples)
SLO holds when invalid_rate <= 0.005 and variance <= variance_threshold
```
Reference Queries
Prometheus:
```promql
(sum(increase(training_loss_invalid_total{run_id="$run"}[10ksteps]))
 /
sum(increase(training_loss_samples_total{run_id="$run"}[10ksteps]))) <= 0.005
```
Prometheus (variance recording rule):
```promql
loss_variance_gauge{run_id="$run"} <= loss_variance_threshold{run_id="$run"}
```
Related Signals
- `training_loss` — metric — Prometheus — Scalar loss sample per step
- `training_loss_invalid_total` — metric — Prometheus — Counter of NaN/Inf samples
- `training_loss_samples_total` — metric — Prometheus — Counter of total samples
- `loss_variance_gauge` — metric — Prometheus — Recording rule storing rolling variance

Notes
- Prefer to compute variance via recording rules to avoid expensive promQL at query time; update thresholds per optimizer schedule.

### 3.6 SLO-STAB-002 — Gradient Norm Health

**SLO Summary**  
- **Domain:** Training Stability  
- **ID:** SLO-STAB-002  
- **Objective:** ≤0.1% of gradient norm samples exceed exploding threshold and ≤5% fall below vanishing threshold after warm-up.  
- **Window:** Warm-up excluded; rolling 5000-step window.  
- **Error Budget:** 0.1% for exploding, 5% for vanishing.  
- **Authoritative Backend:** Prometheus  

**SLI Definition**  
- **Name:** Gradient Norm Health SLI  
- **What it measures:** Fraction of gradient samples outside acceptable thresholds.  
- **Why it matters:** Maintains numerical stability and prevents training stalls or divergences.

**SLI Formula (Logical)**
```text
explode_rate = explode_samples / total_gradient_samples
vanish_rate = vanish_samples / total_gradient_samples
SLO holds when explode_rate <= 0.001 and vanish_rate <= 0.05
```
Reference Queries
Prometheus:
```promql
sum(increase(training_gradient_norm_exploding_total{run_id="$run"}[5000steps]))
 /
sum(increase(training_gradient_norm_samples_total{run_id="$run"}[5000steps]))
```
Prometheus (vanishing portion):
```promql
sum(increase(training_gradient_norm_vanishing_total{run_id="$run"}[5000steps]))
 /
sum(increase(training_gradient_norm_samples_total{run_id="$run"}[5000steps]))
```
Related Signals
- `training_gradient_norm` — metric — Prometheus — Scalar gradient norm per update
- `training_gradient_norm_exploding_total` — metric — Prometheus — Counter for samples above threshold
- `training_gradient_norm_vanishing_total` — metric — Prometheus — Counter for samples below threshold
- `training_gradient_norm_samples_total` — metric — Prometheus — Counter of evaluated samples

Notes
- Thresholds should track optimizer configs; record them as labels (`threshold="explode"`).

### 3.7 SLO-EXP-001 — Epsilon Schedule Health

**SLO Summary**  
- **Domain:** Exploration & Policy  
- **ID:** SLO-EXP-001  
- **Objective:** Epsilon values stay within ±10% of configured schedule and reach minimum before 80% of planned episodes.  
- **Window:** Entire run, monitored via per-episode epsilon samples.  
- **Error Budget:** ≤10% deviation per episode and ≤20% schedule delay.  
- **Authoritative Backend:** Prometheus  

**SLI Definition**  
- **Name:** Epsilon Schedule SLI  
- **What it measures:** Absolute deviation between actual epsilon and planned schedule plus schedule completion timing.  
- **Why it matters:** Ensures exploration annealing behaves as intended, preventing premature exploitation or over-exploration.

**SLI Formula (Logical)**
```text
deviation = |epsilon_actual - epsilon_planned| / epsilon_planned
min_reached_episode <= 0.80 * total_planned_episodes
SLO holds when deviation <= 0.10 for >=99% of samples and min reached before 80%
```
Reference Queries
Prometheus:
```promql
1 - (sum_over_time(epsilon_out_of_band{run_id="$run"}[all]))
  / sum_over_time(agent_epsilon_value{run_id="$run" > 0}[all])
```
Prometheus (minimum reached check):
```promql
last_over_time(agent_epsilon_min_reached_episode{run_id="$run"}[1h])
  <= 0.80 * on(run_id) total_planned_episodes{run_id="$run"}
```
Related Signals
- `agent_epsilon_value` — metric — Prometheus — Gauge of epsilon per episode
- `epsilon_out_of_band` — metric — Prometheus — Counter when deviation exceeds limit
- `agent_epsilon_min_reached_episode` — metric — Prometheus — Episode index when epsilon hits configured minimum
- `total_planned_episodes` — metric — Prometheus — Constant gauge with run plan size

Notes
- Use recording rules to compute `epsilon_out_of_band` flags for alert simplicity; instrumentation should expose planned schedule via config export metric.

### 3.8 SLO-EXP-002 — Policy Entropy Range

**SLO Summary**  
- **Domain:** Exploration & Policy  
- **ID:** SLO-EXP-002  
- **Objective:** Entropy stays above configured floor early, then decays but never collapses to zero prematurely.  
- **Window:** Early phase (first 30% episodes) and late phase (final 20%).  
- **Error Budget:** ≤1% of samples may breach floor/ceiling.  
- **Authoritative Backend:** Prometheus (primary) plus Tempo for per-action spans.  

**SLI Definition**  
- **Name:** Policy Entropy Range SLI  
- **What it measures:** Compliance of measured policy entropy with floor/ceiling envelopes across training phases.  
- **Why it matters:** Alerts if the policy becomes deterministic too soon or fails to converge, both of which degrade performance.

**SLI Formula (Logical)**
```text
floor_breach_rate = breaches_entropy_floor / samples_phase_early
collapse_breach_rate = breaches_entropy_ceiling / samples_phase_late
SLO holds when both rates <= 0.01
```
Reference Queries
Prometheus:
```promql
sum(increase(agent_policy_entropy_floor_breach_total{phase="early", run_id="$run"}[30%episodes]))
 /
sum(increase(agent_policy_entropy_samples_total{phase="early", run_id="$run"}[30%episodes]))
```
Tempo:
```text
service.name="agent" AND span.name="agent.select_action" | entropy < $floor or entropy > $ceiling
```
Related Signals
- `agent_policy_entropy` — metric — Prometheus — Gauge of average entropy per episode
- `agent_policy_entropy_floor_breach_total` — metric — Prometheus — Counter of breaches
- `agent_policy_entropy_samples_total` — metric — Prometheus — Counter of samples per phase
- `agent.select_action` — trace — Tempo — Span attribute `entropy`

Notes
- Tempo queries support per-action verification when metrics show anomalies; store entropy in span attributes for deep dives.

### 3.9 SLO-LAT-001 — Agent Action Latency

**SLO Summary**  
- **Domain:** Latency / Interaction  
- **ID:** SLO-LAT-001  
- **Objective:** p95 ≤ 50 ms and p99 ≤ 100 ms for agent action selection.  
- **Window:** Rolling 15-minute intervals per trainer instance.  
- **Error Budget:** ≤5% of windows may violate either percentile per run day.  
- **Authoritative Backend:** Tempo (primary) with Prometheus histogram optional.  

**SLI Definition**  
- **Name:** Agent Action Latency SLI  
- **What it measures:** Tail latency of `agent.select_action` spans.  
- **Why it matters:** High latency bottlenecks the environment loop and wastes GPU/CPU cycles.

**SLI Formula (Logical)**
```text
p95(agent_action_latency) <= 50ms AND p99(agent_action_latency) <= 100ms
```
Reference Queries
Tempo:
```text
service.name="agent" AND span.name="agent.select_action" | quantile(duration_ms, 0.95) < 50 and quantile(duration_ms, 0.99) < 100
```
Prometheus (if histogram `agent_action_latency_ms_bucket` exists):
```promql
histogram_quantile(0.95, sum(rate(agent_action_latency_ms_bucket{run_id="$run"}[15m])) by (le))
```
Related Signals
- `agent.select_action` — trace — Tempo — Span timings for action selection
- `agent_action_latency_ms_bucket` — metric — Prometheus — Histogram of action duration

Notes
- Align Tempo and Prometheus clocks by ingesting synchronized timestamps; prefer Tempo as source of truth when both exist.

### 3.10 SLO-LAT-002 — Episode Reset Latency

**SLO Summary**  
- **Domain:** Latency / Interaction  
- **ID:** SLO-LAT-002  
- **Objective:** p95 env reset latency ≤ 100 ms, p99 ≤ 250 ms.  
- **Window:** Rolling 30-minute intervals or 100 resets, whichever is larger.  
- **Error Budget:** ≤10% of windows allowed above thresholds.  
- **Authoritative Backend:** Tempo  

**SLI Definition**  
- **Name:** Episode Reset Latency SLI  
- **What it measures:** Tail latency of environment reset spans (`env.reset`, `battleship.engine.setup_random`).  
- **Why it matters:** Slow resets throttle throughput and mask environment regressions.

**SLI Formula (Logical)**
```text
p95(env_reset_latency) <= 100ms AND p99(env_reset_latency) <= 250ms
```
Reference Queries
Tempo:
```text
(service.name="environment" AND span.name="env.reset") OR span.name="battleship.engine.setup_random" | quantile(duration_ms, 0.95) < 100 and quantile(duration_ms, 0.99) < 250
```
Related Signals
- `env.reset` — trace — Tempo — Span measuring environment reset
- `battleship.engine.setup_random` — trace — Tempo — Span nested under reset for placement setup

Notes
- When resets exceed thresholds, capture Loki logs containing `reset_latency_warning` for triage.

### 3.11 SLO-ENV-001 — Placement Success Rate

**SLO Summary**  
- **Domain:** Environment / Engine Integrity  
- **ID:** SLO-ENV-001  
- **Objective:** Placement success rate ≥ 99.9% across all episodes.  
- **Window:** Per run aggregated across entire episode set.  
- **Error Budget:** ≤0.1% placement failures per run.  
- **Authoritative Backend:** Prometheus with Loki for detail.  

**SLI Definition**  
- **Name:** Placement Success SLI  
- **What it measures:** Ratio of successful ship placements to total placement attempts.  
- **Why it matters:** Ensures environment integrity, preventing invalid starting states.

**SLI Formula (Logical)**
```text
successes / (successes + failures) >= 0.999
```
Reference Queries
Prometheus:
```promql
sum(increase(env_placement_success_total{run_id="$run"}[run]))
 /
(sum(increase(env_placement_success_total{run_id="$run"}[run]))
 + sum(increase(env_placement_failures_total{run_id="$run"}[run])))
```
Loki:
```logql
{app="environment", level="error", msg="placement_failure"} | json | count_over_time([1h])
```
Related Signals
- `env_placement_success_total` — metric — Prometheus — Counter of successful placements
- `env_placement_failures_total` — metric — Prometheus — Counter of failures
- `placement_failure` — log — Loki — Structured log entries for each failure

Notes
- Logs should include `board_seed`, `ship_type`, and `run_id` labels for replay.

### 3.12 SLO-ENV-002 — Invalid Action Rejection Rate

**SLO Summary**  
- **Domain:** Environment / Engine Integrity  
- **ID:** SLO-ENV-002  
- **Objective:** Invalid action rejection rate ≤ 0.05% per 10,000 agent actions.  
- **Window:** Rolling 10,000-action window per run.  
- **Error Budget:** 0.05% invalid actions before intervention.  
- **Authoritative Backend:** Prometheus with Loki context.  

**SLI Definition**  
- **Name:** Invalid Action Rejection SLI  
- **What it measures:** Fraction of agent-issued actions that the environment rejects for illegality (duplicate attacks, off-board coordinates, etc.).  
- **Why it matters:** High rejection rates indicate broken masking or action pipelines, wasting steps and corrupting learning signals.

**SLI Formula (Logical)**
```text
invalid_actions / total_actions <= 0.0005
```
Reference Queries
Prometheus:
```promql
sum(increase(env_invalid_action_total{run_id="$run"}[10ksteps]))
  /
sum(increase(env_actions_total{run_id="$run"}[10ksteps]))
```
Loki:
```logql
{app="environment", msg="invalid_action"} | json | count_over_time([10m])
```
Related Signals
- `env_invalid_action_total` — metric — Prometheus — Counter incremented when environment rejects an action
- `env_actions_total` — metric — Prometheus — Counter of attempted actions
- `invalid_action` — log — Loki — Structured log entry containing reason and coordinates

Notes
- Segment by `reason` label (e.g., `duplicate_shot`, `out_of_bounds`) to isolate policy vs. engine regressions before halting runs.

### 3.13 SLO-ENV-003 — Board State Consistency

**SLO Summary**  
- **Domain:** Environment / Engine Integrity  
- **ID:** SLO-ENV-003  
- **Objective:** Board validation pass rate = 100% across sampled episodes.  
- **Window:** Rolling sample of the last 2000 board validation checks.  
- **Error Budget:** 0 tolerance; any failure pauses the run.  
- **Authoritative Backend:** Prometheus with Loki for failure detail.  

**SLI Definition**  
- **Name:** Board State Consistency SLI  
- **What it measures:** Whether generated board states pass structural validation (no overlapping ships, consistent hit markers).  
- **Why it matters:** Invalid boards break fairness assumptions and invalidate training statistics.

**SLI Formula (Logical)**
```text
consistency = validation_failures / (validation_passes + validation_failures)
SLO holds when consistency == 0
```
Reference Queries
Prometheus:
```promql
sum(increase(env_board_state_validation_fail_total{run_id="$run"}[2000checks]))
```
Loki:
```logql
{app="environment", msg="board_validation"} |= "failed" | json
```
Related Signals
- `env_board_state_validation_pass_total` — metric — Prometheus — Counter of successful board validations
- `env_board_state_validation_fail_total` — metric — Prometheus — Counter of failed validations
- `board_validation` — log — Loki — JSON payload describing the invalid condition

Notes
- Validation metrics should attach `validator_version` labels so regressions caused by tooling upgrades are easy to spot.

### 3.14 SLO-ENV-004 — Environment Step Latency

**SLO Summary**  
- **Domain:** Environment / Engine Integrity  
- **ID:** SLO-ENV-004  
- **Objective:** p95 `env.step` latency ≤ 20 ms, p99 ≤ 50 ms.  
- **Window:** Rolling 15-minute window or 500 steps, whichever is larger.  
- **Error Budget:** ≤5% of windows may violate either percentile.  
- **Authoritative Backend:** Tempo (primary) with Prometheus histograms if available.  

**SLI Definition**  
- **Name:** Environment Step Latency SLI  
- **What it measures:** Tail latency for each environment `step` call including engine updates.  
- **Why it matters:** Slow steps throttle episode throughput and mask compute saturation issues.

**SLI Formula (Logical)**
```text
p95(env_step_latency) <= 20ms AND p99(env_step_latency) <= 50ms
```
Reference Queries
Tempo:
```text
service.name="environment" AND span.name="env.step" | quantile(duration_ms, 0.95) < 20 and quantile(duration_ms, 0.99) < 50
```
Prometheus:
```promql
histogram_quantile(0.95, sum(rate(env_step_latency_ms_bucket{run_id="$run"}[15m])) by (le))
```
Related Signals
- `env.step` — trace — Tempo — Span capturing individual step duration
- `env_step_latency_ms_bucket` — metric — Prometheus — Histogram of step latency (optional)

Notes
- When latency spikes correlate with specific `board_seed` or `opponent_type` labels, bubble findings to training scheduling to rebalance workloads.

### 3.15 SLO-ENV-005 — Reward Integrity

**SLO Summary**  
- **Domain:** Environment / Engine Integrity  
- **ID:** SLO-ENV-005  
- **Objective:** Reward integrity mismatch rate = 0 across sampled episodes.  
- **Window:** Rolling 1000-episode validation sample per run.  
- **Error Budget:** 0 mismatches; any mismatch triggers investigation.  
- **Authoritative Backend:** Prometheus with Loki context.  

**SLI Definition**  
- **Name:** Reward Integrity SLI  
- **What it measures:** Comparison between real-time episode rewards and canonical re-computation performed asynchronously.  
- **Why it matters:** Ensures reward shaping logic remains deterministic and prevents silent scoring drift.

**SLI Formula (Logical)**
```text
reward_mismatches / reward_integrity_checks == 0
```
Reference Queries
Prometheus:
```promql
sum(increase(reward_integrity_mismatch_total{run_id="$run"}[1000episodes]))
  /
sum(increase(reward_integrity_check_total{run_id="$run"}[1000episodes]))
```
Loki:
```logql
{app="trainer", msg="reward_integrity_failure"}
```
Related Signals
- `reward_integrity_check_total` — metric — Prometheus — Counter for completed reward audits
- `reward_integrity_mismatch_total` — metric — Prometheus — Counter for mismatched reward calculations
- `reward_integrity_failure` — log — Loki — Payload with episode id, seeds, and expected vs. actual rewards

Notes
- When mismatches appear, freeze policy checkpoints from that run until the scoring code is patched and re-validated.

### 3.16 SLO-OBS-001 — Telemetry Drop Rate

**SLO Summary**  
- **Domain:** Observability Pipeline  
- **ID:** SLO-OBS-001  
- **Objective:** Telemetry drop rate < 0.1% for spans and metrics over any 1-hour window.  
- **Window:** 1-hour sliding windows.  
- **Error Budget:** 0.1% drops; exceeding for ≥2 consecutive windows triggers incident.  
- **Authoritative Backend:** Prometheus (otelcol metrics) with Loki for error logs.  

**SLI Definition**  
- **Name:** Telemetry Drop Rate SLI  
- **What it measures:** Percentage of telemetry units dropped or failed to export relative to accepted volume.  
- **Why it matters:** High drop rates invalidate every other SLO and block debugging.

**SLI Formula (Logical)**
```text
drop_rate = dropped / (dropped + exported) <= 0.001 for spans and metrics
```
Reference Queries
Prometheus:
```promql
sum(increase(otelcol_dropped_spans_total[1h]))
 /
(sum(increase(otelcol_dropped_spans_total[1h])) + sum(increase(otelcol_exported_spans_total[1h])))
```
Loki:
```logql
{component="otelcol", level="error"} |= "Failed to send" | count_over_time([1h])
```
Related Signals
- `otelcol_dropped_spans_total` — metric — Prometheus — Counter of dropped spans
- `otelcol_exported_spans_total` — metric — Prometheus — Counter of successfully exported spans
- `otelcol_dropped_metrics_total` — metric — Prometheus — Counter of dropped metric points
- `otelcol_exported_metrics_total` — metric — Prometheus — Counter of exported metric points
- `otelcol_error_logs` — log — Loki — Collector failure logs

Notes
- Maintain separate SLIs for spans and metrics; whichever breaches first consumes the shared error budget.

### 3.17 SLO-OBS-002 — Exporter Reliability

**SLO Summary**  
- **Domain:** Observability Pipeline  
- **ID:** SLO-OBS-002  
- **Objective:** No extended exporter failure periods; send failure rate remains near zero.  
- **Window:** 30-minute rolling window.  
- **Error Budget:** ≤0.05 retries per second sustained; ≤5 consecutive minutes of failure.  
- **Authoritative Backend:** Prometheus and Loki.  

**SLI Definition**  
- **Name:** Exporter Reliability SLI  
- **What it measures:** Frequency and duration of OTEL exporter send failures across signals.  
- **Why it matters:** Exporter outages silently destroy signals, so they must recover quickly or trigger failover.

**SLI Formula (Logical)**
```text
send_failure_rate = send_failed / total_send_attempts
max_consecutive_failure_duration <= 5m
```
Reference Queries
Prometheus:
```promql
sum(rate(otelcol_exporter_send_failed_spans_total[5m]) + rate(otelcol_exporter_send_failed_metrics_total[5m]))
```
Loki:
```logql
{component="otelcol", level="error"} |= "exporter" |= "permanent error"
```
Related Signals
- `otelcol_exporter_send_failed_spans_total` — metric — Prometheus — Failed span exports
- `otelcol_exporter_send_failed_metrics_total` — metric — Prometheus — Failed metric exports
- `otelcol_exporter_permanent_error` — log — Loki — Exporter fatal errors

Notes
- Track exporter-specific labels (`exporter="tempo"`) to isolate partial outages.

### 3.18 SLO-OBS-003 — Collector Queue Pressure

**SLO Summary**  
- **Domain:** Observability Pipeline  
- **ID:** SLO-OBS-003  
- **Objective:** p95 queue pressure ≤ 0.5 and p99 ≤ 0.7 over 30 minutes.  
- **Window:** Sliding 30-minute windows.  
- **Error Budget:** ≤5% windows may violate thresholds.  
- **Authoritative Backend:** Prometheus  

**SLI Definition**  
- **Name:** Collector Queue Pressure SLI  
- **What it measures:** Utilization ratio of OTEL collector queues relative to capacity.  
- **Why it matters:** Sustained pressure predicts impending drops or latency increases.

**SLI Formula (Logical)**
```text
p95(queue_pressure) <= 0.5 AND p99(queue_pressure) <= 0.7
```
Reference Queries
Prometheus:
```promql
histogram_quantile(0.95, sum(rate(otelcol_queue_pressure_bucket[30m])) by (le))
```
Prometheus (p99):
```promql
histogram_quantile(0.99, sum(rate(otelcol_queue_pressure_bucket[30m])) by (le))
```
Related Signals
- `otelcol_queue_pressure` — metric — Prometheus — Gauge/histogram of queue utilization
- `otelcol_queue_pressure_bucket` — metric — Prometheus — Histogram buckets per collector queue

Notes
- Alerting should fan out to training operators because high queue pressure often precedes telemetry loss incidents.

## 4. Error Budget Policy
Error budgets in this experimental RL stack translate policy targets into actionable guardrails. Each SLO consumes a portion of the total reliability allowance; breaches signal whether we are over-spending the allowance in pursuit of new experiments.

Learning progress violations (e.g., multi-window reward regressions or sub-60% win rate) consume the improvement budget. If two consecutive evaluation windows breach, pause the run, analyze reward distributions, and adjust curriculum or opponent mix before resuming. Hyperparameter sweeps should not continue while the primary learning SLO is failing.

Stability violations, such as repeated NaN/Inf losses or gradient norm explosions, immediately halt affected runs. Operators should snapshot weights, inspect optimizer settings, and consider reducing learning rate or clipping thresholds. Restarts must only occur after verifying instrumentation and ensuring stale gradients are discarded.

Observability breaches—telemetry drops, exporter failures, or collector queue saturation—invalidate all other SLO outcomes. The prescribed response is to fix the telemetry pipeline first (scaling collectors, clearing back-pressure, patching exporters), re-run the affected training segments, and rebaseline metrics. Do not declare SLO compliance using data gathered while observability SLOs were violated.

If repeated error budget consumption stems from changed objectives (e.g., harder environment or new agents), update the SLOs/SLIs in this document and synchronize the observability catalogue accordingly. Governance reviews should confirm whether target adjustments are justified or if engineering fixes are required.

## 5. Backend Mapping
| Backend | Primary Role | Examples |
|---------|--------------|----------|
| Prometheus | Numeric SLIs for learning/performance metrics, training stability, collector health | `battleship_episode_win`, `training_gradient_norm`, `otelcol_queue_pressure` |
| Loki | Structured failure logs for environment and telemetry debugging | `placement_failure` logs, `otelcol exporter` errors |
| Tempo | Latency and interaction traces for agent actions and environment resets | `agent.select_action`, `env.reset`, per-action entropy spans |

## 6. Linkage to Observability Catalogue
This `slo_sli_reference.md` file defines the governance-level SLOs and corresponding SLIs. The companion `docs/observability_catalogue.md` enumerates the detailed signals, implementation locations, and per-backend query examples used to realize each SLI. Every SLO/SLI listed here should map to one or more catalogue rows; when an SLO changes, update both this reference and the catalogue so dashboards, alerts, and runbooks stay aligned.

## 7. Change Log
- 2025-01-18 — Initial version of SLO & SLI reference created.
