# 1 Global_Planning_And_Foundations
## 1.1 Repository_And_Tooling_Setup
### 1.1.1 Initialize_Repository_And_Project_Structure
- S: DONE
- D: Lay down the repository skeleton, configure lint/test/type-check tooling, and scaffold initial Makefile targets.
- AC:
  - Repository includes src/, tests/, docs/, and pyproject files committed with initial README as defined in the architecture standards.
### 1.1.2 Configure_Linting_Testing_And_Typechecking_Tools
- S: DONE
- D: Lay down the repository skeleton, configure lint/test/type-check tooling, and scaffold initial Makefile targets.
- AC:
  - Ruff/black/mypy/pytest configurations run cleanly via a single make target on a fresh clone.
### 1.1.3 Create_Initial_Makefile_Scaffold
- S: DONE
- D: Lay down the repository skeleton, configure lint/test/type-check tooling, and scaffold initial Makefile targets.
- AC:
  - `Makefile` exposes at least `make lint`, `make test`, and `make typecheck` targets wired to the configured tools.
## 1.2 Architecture_Strategey_And_Standards
### 1.2.1 Define_Container_Boundaries_And_High_Level_Architecture
- S: DONE
- D: Define container boundaries, coding/testing/branching standards, and author architecture/ADR docs.
- AC:
  - Published diagram lists every major container/web UI/API/engine component with clear boundaries and responsibilities.
### 1.2.2 Define_Coding_Testing_And_Branching_Standards
- S: DONE
- D: Define container boundaries, coding/testing/branching standards, and author architecture/ADR docs.
- AC:
  - CONTRIBUTING or similar doc spells out coding style, branching model, PR review expectations, and required checks.
### 1.2.3 Create_Initial_Architecture_And_ADR_Documents
- S: DONE
- D: Define container boundaries, coding/testing/branching standards, and author architecture/ADR docs.
- AC:
  - Architecture doc and ADRs exist in docs/ with version-controlled decisions for core technology choices.
# 2 Core_Game_Engine_And_Gym_Environment
## 2.1 Engine_Implementation
### 2.1.1 Implement_Ship_Board_And_Game_Logic
- S: DONE
- D: Implement ship, board, and game logic with deterministic rules and robust error handling.
- AC:
  - Engine passes tests proving ships, boards, and turn rotation behave deterministically for varied inputs.
### 2.1.2 Implement_Deterministic_Rules_And_Error_Handling
- S: DONE
- D: Implement ship, board, and game logic with deterministic rules and robust error handling.
- AC:
  - Invalid moves, overlaps, and rule violations raise explicit errors covered by regression tests.
## 2.2 Gym_Environment_Implementation
### 2.2.1 Design_Action_And_Observation_Spaces
- S: DONE
- D: Design action and observation spaces, then implement the Battleship Gym environment.
- AC:
  - Action/observation spaces documented and encoded so Gymnasium validates them without warnings.
### 2.2.2 Implement_Battleship_Gym_Environment
- S: DONE
- D: Design action and observation spaces, then implement the Battleship Gym environment.
- AC:
  - `BattleshipEnv` registers with Gymnasium and returns deterministic observations/rewards for scripted matches.
## 2.3 Engine_And_Environment_Testing
### 2.3.1 Create_Engine_Unit_Tests
- S: DONE
- D: Create engine unit tests plus environment unit/integration suites to verify behaviour.
- AC:
  - Pytest suite asserts board state transitions, win detection, and error cases for the engine module.
### 2.3.2 Create_Environment_Unit_And_Integration_Tests
- S: DONE
- D: Create engine unit tests plus environment unit/integration suites to verify behaviour.
- AC:
  - Environment tests simulate multi-turn episodes and ensure resets/steps align with Gym specs.
## 2.4 Engine_And_Environment_Documentation
### 2.4.1 Document_Battleship_Rules
- S: DONE
- D: Document Battleship rules and the Gym environment contract for consumers.
- AC:
  - Markdown doc enumerates setup, turn order, victory conditions, and edge rules referenced by APIs.
### 2.4.2 Document_Gym_Environment_Contract
- S: DONE
- D: Document Battleship rules and the Gym environment contract for consumers.
- AC:
  - Contract doc details observation tensors, action masks, rewards, and episode termination semantics.
## 2.5 Makefile_Integration_For_Engine_And_Environment
### 2.5.1 Add_Make_Targets_For_Engine_And_Environment_Tests
- S: DONE
- D: Add Makefile targets that run engine and environment test suites.
- AC:
  - `make test-engine` (or equivalent) runs targeted engine/env suites locally and in CI.
# 3 RL_Agent_And_Training_Orchestrator
## 3.1 RL_Agent_Implementation
### 3.1.1 Implement_DQN_Network_Architecture
- S: DONE
- D: Implement the DQN network architecture along with replay buffer and epsilon-greedy policy.
- AC:
  - DQN model class builds without shape errors and exposes forward/inference methods used by training loop.
### 3.1.2 Implement_Replay_Buffer_And_Epsilon_Greedy_Policy
- S: DONE
- D: Implement the DQN network architecture along with replay buffer and epsilon-greedy policy.
- AC:
  - Replay buffer maintains configurable capacity and epsilon schedule adjustable via config.
## 3.2 Training_Orchestrator_Implementation
### 3.2.1 Implement_Training_Loop_And_Config_Structure
- S: DONE
- D: Build the training loop/configuration system plus evaluation and rollout utilities.
- AC:
  - Training entrypoint reads config, runs episodes, checkpoints weights, and logs metrics per policy.
### 3.2.2 Implement_Evaluation_And_Policy_Rollout_Utilities
- S: DONE
- D: Build the training loop/configuration system plus evaluation and rollout utilities.
- AC:
  - Evaluation utilities pit latest model vs baselines and capture win-rate/policy rollout summaries.
## 3.3 RL_Agent_And_Training_Testing
### 3.3.1 Create_Network_And_Buffer_Tests
- S: DONE
- D: Author tests for networks, buffers, training steps, and sanity checks.
- AC:
  - Tests cover tensor dimensions, gradient flows, and buffer push/pop ordering.
### 3.3.2 Create_Training_Step_And_Sanity_Tests
- S: DONE
- D: Author tests for networks, buffers, training steps, and sanity checks.
- AC:
  - Training-step tests ensure rewards accumulate, epsilon decays, and checkpoints emit without errors.
## 3.4 RL_Agent_And_Training_Documentation
### 3.4.1 Document_Training_Configuration_And_Defaults
- S: DONE
- D: Document training configuration defaults and overall RL design decisions.
- AC:
  - Config reference lists default hyperparameters, CLI flags, and expected artifact locations.
### 3.4.2 Record_RL_Algorithm_And_Design_Decisions
- S: DONE
- D: Document training configuration defaults and overall RL design decisions.
- AC:
  - ADR or design note documents algorithm selection, network architecture, and exploration rationale.
## 3.5 Makefile_Integration_For_RL
### 3.5.1 Add_Make_Targets_For_RL_Tests_And_Training_Commands
- S: DONE
- D: Add Makefile targets covering RL tests and training commands.
- AC:
  - Makefile exposes `make rl-test` and `make train` commands used in docs and CI scripts.
# 4 Telemetry_Foundation
## 4.1 Telemetry_Library_Implementation
### 4.1.1 Implement_Telemetry_Configuration_Module
- S: DONE
- D: Implement telemetry configuration modules along with tracer, meter, and logger helpers.
- AC:
  - Telemetry config module reads env vars, sets service/resource attributes, and initializes exporters lazily.
### 4.1.2 Implement_Tracer_Metrics_And_Logger_Helpers
- S: DONE
- D: Implement telemetry configuration modules along with tracer, meter, and logger helpers.
- AC:
  - Helper functions return shared OTEL tracer/meter/logger instances with namespace tagging.
## 4.2 Telemetry_Instrumentation_Of_Core_Services
### 4.2.1 Instrument_Engine_And_Game_Flow
- S: DONE
- D: Instrument the Battleship engine and core game flow with OTEL spans, metrics, and logs that work cleanly with Prometheus, Tempo, and Loki.
- AC:
  - Spans:
    - `setup_random`, `make_move`, and game completion emit OTEL spans with stable names, e.g.:
      - `battleship.engine.setup_random`
      - `battleship.engine.make_move`
      - `battleship.engine.game_complete`
    - A top-level game/episode span exists (e.g. `battleship.engine.game`), and per-move spans are children of this span, forming a clear parent–child chain for the whole game.
    - All engine/game spans share a small, consistent attribute set, such as:
      - `service.name`, `environment`
      - `game_id`
      - `player` (e.g. `player1|player2`)
      - `phase` (e.g. `setup|in_progress|finished`)
      - `outcome` on completion spans (e.g. `win|loss`)
      - `shot_result` on move spans (e.g. `hit|miss|sunk`, optional `ship_type`)
    - Span attributes avoid high-cardinality / unbounded values (no per-span UUID labels, no raw stack traces, no full board dumps).
  - Metrics:
    - Engine emits Prometheus-friendly metrics via the shared meter, including at minimum:
      - `battleship_game_started_total`
      - `battleship_game_completed_total{outcome=...}`
      - `battleship_shots_total{result=hit|miss|sunk,player=...}`
      - `battleship_game_duration_seconds` as a histogram.
    - Metric label sets are small and bounded (e.g. player, result, outcome only), avoiding labels based on coordinates, IDs, or arbitrary strings.
  - Logs:
    - Key engine events emit structured logs (e.g. game start, invalid move, game complete, critical errors) through the shared logger.
    - Logs include correlation fields such as `trace_id` (and `game_id`, `player`) so they can be joined with traces and metrics in Loki/Tempo.
  - Integration pattern:
    - All engine/game flow instrumentation uses the central `battleship.telemetry` API (tracer, meter, logger), with no direct references to exporters or backend-specific clients in engine code.

### 4.2.2 Instrument_Gym_Environment_And_RL_Agent
- S: DONE
- D: Instrument the Gym environment and RL agent with OTEL spans, metrics, and structured logs, using the shared battleship.telemetry interfaces and producing signals compatible with Prometheus, Tempo, and Loki.
- AC:
  - Spans — Gym Environment:
    - `reset()` and `step()` emit spans with stable names:
      - `battleship.env.reset`
      - `battleship.env.step`
    - Each environment span is a child of the current game/episode span (established by engine instrumentation).
    - Spans include low-cardinality attributes, such as:
      - `episode_id`
      - `action_valid` (`true|false`)
      - `terminated` (`true|false`)
      - `truncated` (`true|false`)
      - `reward_type` (e.g. `hit|miss|win|loss|invalid` — bounded vocabulary)
    - No high-cardinality attributes (no raw observations, no coordinate labels, no full game snapshots).

  - Spans — RL Agent:
    - `select_action()` and `train_step()` emit spans with stable names:
      - `battleship.agent.select_action`
      - `battleship.agent.train_step`
    - Span attributes include:
      - `agent_id` (small finite set, not UUID per-episode)
      - `policy_mode` (`explore|exploit`)
      - `epsilon` (rounded to 3 decimals to avoid cardinality explosion)
      - `batch_size` (training only)
    - No unbounded attributes (e.g. no full Q-value arrays, no arbitrary debug strings).

  - Metrics — Gym Environment:
    - Counters:
      - `battleship_env_actions_total{result=valid|invalid}`
      - `battleship_env_resets_total`
    - Histograms:
      - `battleship_env_step_duration_seconds`
      - `battleship_env_reward_value` (optional histogram)
    - Label sets are strictly bounded (e.g. `result`, `terminated`, never coordinates or large IDs).

  - Metrics — RL Agent:
    - Counters:
      - `battleship_agent_training_steps_total`
    - Histograms:
      - `battleship_agent_inference_duration_seconds`
      - `battleship_agent_training_loss`
      - `battleship_agent_training_step_duration_seconds`
    - Labels restricted to small fixed sets (e.g. `policy_mode` only).

  - Logs:
    - Structured logs via the shared battleship.telemetry logger for:
      - `select_action` decisions (action chosen, explore/exploit, epsilon)
      - training errors, NaN detection, or divergence warnings
      - invalid-action attempts in the environment
    - Logs include correlation IDs (`trace_id`, `episode_id`) so they join to traces and metrics in Loki/Tempo.

  - Integration Pattern:
    - All instrumentation must use the unified telemetry API in `battleship.telemetry` (tracer, meter, logger).
    - No exporter configuration, OTLP clients, environment-specific SDK setup, or direct Prometheus/Tempo/Loki references appear inside env/agent modules.
    - Instrumentation adds minimal overhead and does not change environment/agent semantics or determinism.

## 4.3 Telemetry_Testing
### 4.3.1 Create_Lazy_Init_And_NoOp_Telemetry_Tests
- S: DONE
- D: Write tests for lazy init/no-op flows and for span/metric emission.
- AC:
  - Tests prove telemetry init no-ops when disabled and only runs once when enabled.
### 4.3.2 Create_Tests_For_Span_And_Metric_Emission
- S: TODO
- D: Write tests for lazy init/no-op flows and for span/metric emission.
- AC:
  - Unit tests assert span/metric exporters receive expected names and attributes during sample runs.
## 4.4 Telemetry_Documentation
### 4.4.1 Document_Telemetry_Design_And_Naming_Conventions
- S: DONE
- D: Document telemetry design choices and naming conventions.
- AC:
  - Telemetry doc lists namespace conventions, attribute keys, and exporter wiring steps.
## 4.5 Makefile_Integration_For_Telemetry
### 4.5.1 Add_Make_Targets_For_Telemetry_Test_Suites
- S: DONE
- D: Add Makefile targets to run telemetry test suites.
- AC:
  - `make telemetry-test` executes only the telemetry suites locally and in CI.
# 5 Persistence_And_Data_Model
## 5.1 Data_Model_Implementation
### 5.1.1 Implement_SQL_ORM_Models
- S: TODO
- D: Implement SQL ORM models plus database session and repository helpers.
- AC:
  - ORM models define tables/relationships for users, rooms, matches, moves, agents, ratings, and jobs.
### 5.1.2 Implement_Database_Session_And_Repository_Helpers
- S: TODO
- D: Implement SQL ORM models plus database session and repository helpers.
- AC:
  - Session/repository helpers expose context-managed transactions and CRUD helpers for API use.
## 5.2 Migrations_And_Schema_Management
### 5.2.1 Initialize_Migration_Toolchain
- S: TODO
- D: Initialize the migration toolchain and define base/evolution processes.
- AC:
  - Alembic (or equivalent) migration tool initializes with baseline revision checked into repo.
### 5.2.2 Create_Base_Migration_And_Schema_Evolution_Process
- S: TODO
- D: Initialize the migration toolchain and define base/evolution processes.
- AC:
  - Migration scripts handle schema upgrades/downgrades and are documented for release flow.
## 5.3 Persistence_Testing
### 5.3.1 Create_Model_And_Relationship_Tests
- S: TODO
- D: Create model relationship tests and transaction/rollback coverage.
- AC:
  - Tests instantiate in-memory DB, assert FK relationships, and verify cascade behaviors.
### 5.3.2 Create_Transaction_And_Rollback_Tests
- S: TODO
- D: Create model relationship tests and transaction/rollback coverage.
- AC:
  - Transaction tests prove rollback on exceptions and concurrent write handling.
## 5.4 Persistence_Documentation
### 5.4.1 Document_Logical_Data_Model_And_ERD
- S: TODO
- D: Document the logical data model/ERD and database rationale.
- AC:
  - ERD diagram stored in docs/ illustrates key entities/relationships for SQL Server schema.
### 5.4.2 Document_Database_Choice_And_Rationale
- S: TODO
- D: Document the logical data model/ERD and database rationale.
- AC:
  - Document explains why SQL Server chosen plus scaling/backup considerations.
## 5.5 Makefile_Integration_For_Persistence
### 5.5.1 Add_Make_Targets_For_Migrations_And_DB_Tests
- S: TODO
- D: Add Make targets for running migrations and DB tests.
- AC:
  - `make db-test` and `make migrate` targets run migrations and DB suites with one command.
# 6 API_Server_And_Domain_Services
## 6.1 API_Foundation
### 6.1.1 Implement_API_Application_Skeleton
- S: TODO
- D: Implement the API application skeleton plus health and status endpoints.
- AC:
  - FastAPI app factory wires middleware, routers, and settings with health endpoint mounted.
### 6.1.2 Implement_Health_And_Status_Endpoints
- S: TODO
- D: Implement the API application skeleton plus health and status endpoints.
- AC:
  - `/health` and `/status` endpoints return JSON with version/build info and pass monitoring checks.
## 6.2 Domain_Router_And_Service_Implementation
### 6.2.1 Implement_User_And_Identity_Routers
- S: TODO
- D: Implement routers for users/identity, lobby/rooms, matches/AI matches, and agents/ladder/training jobs.
- AC:
  - User/identity routes support me/profile retrieval and map Auth0 subjects to internal users.
### 6.2.2 Implement_Lobby_And_Room_Management_Routers
- S: TODO
- D: Implement routers for users/identity, lobby/rooms, matches/AI matches, and agents/ladder/training jobs.
- AC:
  - Lobby/room routes create/join/list/leave rooms enforcing capacity and status transitions.
### 6.2.3 Implement_Match_And_AI_Match_Routers
- S: TODO
- D: Implement routers for users/identity, lobby/rooms, matches/AI matches, and agents/ladder/training jobs.
- AC:
  - Match routes cover human and AI matches with submit-move and replay retrieval APIs.
### 6.2.4 Implement_Agent_Ladder_And_Training_Job_Routers
- S: TODO
- D: Implement routers for users/identity, lobby/rooms, matches/AI matches, and agents/ladder/training jobs.
- AC:
  - Agent/ladder/training job routers support CRUD plus ladder ranking queries.
## 6.3 WebSocket_Endpoints
### 6.3.1 Implement_Lobby_WebSocket_Channel
- S: TODO
- D: Implement lobby and match WebSocket channels.
- AC:
  - `/ws/lobby` broadcasts room create/update/delete events to subscribed clients with auth checks.
### 6.3.2 Implement_Match_WebSocket_Channel
- S: TODO
- D: Implement lobby and match WebSocket channels.
- AC:
  - `/ws/matches/{id}` streams turn updates/chat events with turn-order validation.
## 6.4 API_Testing
### 6.4.1 Create_REST_Endpoint_Tests
- S: TODO
- D: Create REST and WebSocket endpoint tests.
- AC:
  - REST tests hit happy/sad paths for each route, covering auth failures and validation errors.
### 6.4.2 Create_WebSocket_Endpoint_Tests
- S: TODO
- D: Create REST and WebSocket endpoint tests.
- AC:
  - WebSocket tests simulate join/leave/move flows and assert message schemas.
## 6.5 API_Documentation
### 6.5.1 Document_API_Endpoints_And_Usage
- S: TODO
- D: Document API endpoints, usage patterns, and lobby/match domain flows.
- AC:
  - API reference in docs lists endpoints, parameters, auth requirements, and sample responses.
### 6.5.2 Document_Lobby_And_Match_Domain_Flows
- S: TODO
- D: Document API endpoints, usage patterns, and lobby/match domain flows.
- AC:
  - Domain flow doc diagrams lobby/match lifecycle from room creation through replay archival.
## 6.6 Telemetry_Integration_For_API
### 6.6.1 Instrument_API_Routes_And_WebSockets
- S: TODO
- D: Instrument API routes and WebSockets with telemetry.
- AC:
  - OTEL spans/metrics wrap each API route and WS handler with trace IDs propagated to clients.
## 6.7 Makefile_Integration_For_API
### 6.7.1 Add_Make_Targets_For_API_Test_Suites
- S: TODO
- D: Add Make targets for API test suites.
- AC:
  - Makefile target runs all API unit/integration/ws tests headlessly for CI.
# 7 Authentication_And_Identity
## 7.1 Authentication_Implementation
### 7.1.1 Implement_JWT_Validation_And_User_Resolution
- S: TODO
- D: Implement JWT validation, user resolution, and integrate auth dependencies into routers.
- AC:
  - JWT validator checks issuer/audience/expiry and resolves or creates internal user records.
### 7.1.2 Integrate_Authentication_Dependencies_Into_Routers
- S: TODO
- D: Implement JWT validation, user resolution, and integrate auth dependencies into routers.
- AC:
  - Dependency wiring injects authenticated user context into routers and rejects unauthenticated calls.
## 7.2 Authentication_Testing
### 7.2.1 Create_Tests_For_Token_Validation_Scenarios
- S: TODO
- D: Write tests covering token validation scenarios and authenticated route access.
- AC:
  - Tests cover valid tokens, expired tokens, wrong issuer/audience, and signature failures.
### 7.2.2 Create_Tests_For_Authenticated_Route_Access
- S: TODO
- D: Write tests covering token validation scenarios and authenticated route access.
- AC:
  - Route tests ensure protected endpoints deny anonymous access and allow valid JWTs.
## 7.3 Authentication_Documentation
### 7.3.1 Document_Authentication_And_Authorisation_Flows
- S: TODO
- D: Document authentication and authorisation flows.
- AC:
  - Auth doc diagrams login, token exchange, and backend mapping flows with troubleshooting notes.
## 7.4 Telemetry_Integration_For_Authentication
### 7.4.1 Instrument_Authentication_Spans_And_Metrics
- S: TODO
- D: Instrument authentication spans and metrics.
- AC:
  - Auth spans include login attempts, validation failures, and user resolution metrics.
## 7.5 Makefile_Integration_For_Authentication
### 7.5.1 Add_Make_Targets_For_Authentication_Tests
- S: TODO
- D: Add Make targets for authentication tests.
- AC:
  - `make auth-test` executes only auth suites for rapid feedback.
# 8 Web_Application_HTML_CSS_JS
## 8.1 Web_App_Scaffolding
### 8.1.1 Initialize_Web_Project_Structure
- S: TODO
- D: Initialize the web project structure and configure the build toolchain/dev server.
- AC:
  - Frontend repo contains scaffolded source tree (src/, public/) with lint/build scripts.
### 8.1.2 Configure_Build_Toolchain_And_Dev_Server
- S: TODO
- D: Initialize the web project structure and configure the build toolchain/dev server.
- AC:
  - Dev server hot-reloads and build pipeline outputs optimized bundle via configured toolchain.
## 8.2 Web_Authentication_Integration
### 8.2.1 Integrate_OAuth_SPA_Library
- S: TODO
- D: Integrate the OAuth SPA library and implement login/logout/token handling.
- AC:
  - OAuth SPA lib configured with Auth0 tenant, storing tokens securely per best practices.
### 8.2.2 Implement_Login_Logout_And_Token_Handling
- S: TODO
- D: Integrate the OAuth SPA library and implement login/logout/token handling.
- AC:
  - Login/logout flows refresh tokens, handle expiry, and expose hook/context for API calls.
## 8.3 Web_Feature_Implementation
### 8.3.1 Implement_Lobby_View_And_Interactions
- S: TODO
- D: Implement lobby, match (real-time), ladder, and training jobs views.
- AC:
  - Lobby view renders room list, filters, and actions wired to REST + WS APIs.
### 8.3.2 Implement_Match_View_And_RealTime_Updates
- S: TODO
- D: Implement lobby, match (real-time), ladder, and training jobs views.
- AC:
  - Match view shows boards/replay timeline and updates in real time via WebSocket events.
### 8.3.3 Implement_Ladder_View
- S: TODO
- D: Implement lobby, match (real-time), ladder, and training jobs views.
- AC:
  - Ladder view lists agents, ratings, streaks, and links to agent profiles.
### 8.3.4 Implement_Training_Jobs_View
- S: TODO
- D: Implement lobby, match (real-time), ladder, and training jobs views.
- AC:
  - Training jobs view surfaces job list/detail, start actions, and telemetry snapshots.
## 8.4 Web_Testing
### 8.4.1 Create_Unit_Tests_For_Web_Logic
- S: TODO
- D: Create unit tests for web logic and prep scenarios for end-to-end testing.
- AC:
  - Component/unit tests cover reducers/stores/hooks with >80% critical-path coverage.
### 8.4.2 Prepare_Scenarios_For_E2E_Testing
- S: TODO
- D: Create unit tests for web logic and prep scenarios for end-to-end testing.
- AC:
  - E2E scenario definitions outline key flows (login, create room, play match, view replay).
## 8.5 Web_Documentation
### 8.5.1 Document_Web_UX_And_User_Flows
- S: TODO
- D: Document web UX and user flows.
- AC:
  - UX doc maps primary navigation, user personas, and step-by-step flows for each page.
## 8.6 Web_Telemetry_Integration
### 8.6.1 Integrate_Web_Telemetry_SDK_For_Spans_And_Errors
- S: TODO
- D: Integrate the web telemetry SDK for spans and error tracking.
- AC:
  - Web telemetry captures page loads, API errors, and WS events with OTEL JS exporter configured.
## 8.7 Makefile_Integration_For_Web
### 8.7.1 Add_Make_Targets_For_Web_Build_And_Tests
- S: TODO
- D: Add Make targets for web build and test workflows.
- AC:
  - `make web-build` / `make web-test` automate lint/build/test pipelines.
# 9 Observability_Stack
## 9.1 Observability_Infrastructure_Configuration
### 9.1.1 Configure_Telemetry_Collector_And_Pipelines
- S: TODO
- D: Configure telemetry collectors/pipelines and metrics/tracing/logging backends.
- AC:
  - Alloy/OTLP collector configuration checked into ops/ and verified via docker compose run.
### 9.1.2 Configure_Metrics_Tracing_And_Logging_Backends
- S: TODO
- D: Configure telemetry collectors/pipelines and metrics/tracing/logging backends.
- AC:
  - Prometheus/Grafana/Loki/Tempo configs deployed with credentials and data-retention settings.
## 9.2 Dashboards_And_Analytics
### 9.2.1 Create_Dashboards_For_API_And_Matches
- S: TODO
- D: Create dashboards for API/match activity and RL training/agents.
- AC:
  - Grafana dashboard visualizes API latency, error rates, request volume, and WS activity.
### 9.2.2 Create_Dashboards_For_RL_Training_And_Agents
- S: TODO
- D: Create dashboards for API/match activity and RL training/agents.
- AC:
  - Dashboard for RL shows reward curves, training throughput, and agent ladder stats.
## 9.3 Observability_Smoke_Testing
### 9.3.1 Validate_EndToEnd_Telemetry_Flows
- S: TODO
- D: Validate end-to-end telemetry flows via smoke tests.
- AC:
  - Synthetic trace/log/metric flow proves telemetry travels from app -> collector -> backend.
## 9.4 Observability_Documentation
### 9.4.1 Document_Observability_Stack_Setup
- S: TODO
- D: Document the observability stack setup, SLIs/SLOs, and catalogue.
- AC:
  - Observability runbook documents setup steps for recreating the stack.
### 9.4.2 Document_SLIs_And_SLOs
- S: TODO
- D: Document the observability stack setup, SLIs/SLOs, and catalogue.
- AC:
  - SLIs/SLOs defined with targets for API latency, uptime, match success, and training throughput.
### 9.4.3 Document_Observability_Catalogue
- S: TODO
- D: Document the observability stack setup, SLIs/SLOs, and catalogue.
- AC:
  - Catalogue lists every dashboard/alert with owner and purpose.
## 9.5 Makefile_Integration_For_Observability
### 9.5.1 Add_Make_Targets_For_Starting_And_Stopping_Observability_Services
- S: TODO
- D: Add Make targets for starting/stopping observability services.
- AC:
  - Make targets start/stop observability stack locally for developers.
# 10 Packaging_CI_CD_E2E_Load_And_Chaos
## 10.1 Containerization_And_Compose
### 10.1.1 Implement_Dockerfiles_For_Core_Services
- S: TODO
- D: Implement Dockerfiles for core services and the compose stack definition.
- AC:
  - Dockerfiles build reproducible images for FastAPI, trainer, and supporting services.
### 10.1.2 Implement_Docker_Compose_Stack_Definition
- S: TODO
- D: Implement Dockerfiles for core services and the compose stack definition.
- AC:
  - docker-compose stack starts API, trainer, SQL, and observability services with one command.
## 10.2 CI_CD_Pipeline
### 10.2.1 Define_CI_Pipeline_Stages_And_Requirements
- S: TODO
- D: Define CI pipeline stages/requirements and integrate Makefile CI targets.
- AC:
  - CI pipeline yaml defines lint/test/build/deploy stages with required approvals.
### 10.2.2 Integrate_CI_With_Makefile_CI_Targets
- S: TODO
- D: Define CI pipeline stages/requirements and integrate Makefile CI targets.
- AC:
  - Pipeline invokes Makefile targets rather than duplicating logic, ensuring parity locally vs CI.
## 10.3 EndToEnd_Testing
### 10.3.1 Implement_E2E_Test_Scenarios
- S: TODO
- D: Implement E2E test scenarios and hook them into CI.
- AC:
  - E2E tests simulate core happy paths (login, matchmaking, gameplay) against deployed stack.
### 10.3.2 Integrate_E2E_Tests_Into_CI_Pipeline
- S: TODO
- D: Implement E2E test scenarios and hook them into CI.
- AC:
  - CI job runs E2E suite on demand or nightly and reports artifacts/screenshots on failure.
## 10.4 Load_And_Chaos_Testing
### 10.4.1 Implement_Load_Test_Scenarios
- S: TODO
- D: Implement load-test and chaos-test experiments.
- AC:
  - Load tests document target QPS, run via k6/Gatling/etc., and emit metrics to Grafana.
### 10.4.2 Implement_Chaos_Test_Experiments
- S: TODO
- D: Implement load-test and chaos-test experiments.
- AC:
  - Chaos experiments induce failures (agent crash, DB latency) and verify system recovery.
## 10.5 Operations_Documentation
### 10.5.1 Document_Dev_Environment_Runbook
- S: TODO
- D: Document the dev environment and incident-response runbooks.
- AC:
  - Dev runbook lists prerequisites, setup steps, common issues, and escalation paths.
### 10.5.2 Document_Incident_Response_Runbook
- S: TODO
- D: Document the dev environment and incident-response runbooks.
- AC:
  - Incident response guide defines severity levels, communication templates, and mitigation steps.
## 10.6 Makefile_Integration_For_CI_CD_And_Operations
### 10.6.1 Add_Make_Targets_For_Build_Test_Deploy_And_Operational_Tasks
- S: TODO
- D: Add Make targets for build/test/deploy and operational tasks.
- AC:
  - Make operations target chains build/test/deploy plus start load/chaos/obs tooling as needed.
