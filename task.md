# Implementation Tasks: AI-Powered Test Case Generator

**Document Status:** Master Task Backlog  
**Governed by:** `constitution.md`, `prd.md`, `spec.md`, `skills.md`, and `plan.md`  
**Execution Guidance:** Tasks must be implemented in logical dependency order. Every task is designed to be independently executable by GitHub Copilot or a software engineer.

## Implementation Progress (2026-08-27)

The first end-to-end vertical slice is implemented and validated against the fictional sample corpus. The web application, local CLI, deterministic evidence-grounded generator for offline tests, Google AI Studio provider boundary configured for Gemma 4:31B, Excel/Markdown/PDF source adapters, normalization, traceability, validation, coverage, storage, security scanning, and JSON/CSV/XLSX exports are operational. The browser workflow covers Dashboard, Documents, Generate Tests, Test Cases, Traceability, Coverage, and Reports.

Generation recovery update: Google JSON envelope parsing now accepts JSON-only Markdown wrappers, provider retries are bounded, generation outcomes are returned by scenario type, and transient or malformed Google responses can produce explicitly labeled deterministic evidence fallbacks. The active sample run has 57 cases across all seven scenario classes; fallback use and provider failures remain visible for human review.

Report presentation update: the Reports screen now renders human-readable Summary, Coverage, Traceability, Quality, Review, and Change Impact previews with executive metrics, status indicators, action points, and detail tables. Raw JSON remains available through the structured export actions.

Review signals update: the web state now separates active unresolved signals from historical warnings. A generation failure is removed from the active signal list once the corresponding requirement and scenario type has a persisted case; genuine gaps and explicitly labeled fallback-review notices remain visible.

Review and criteria update: Dashboard case totals now show approved, awaiting-review, and rejected breakdowns. Approved status is preserved when validation is rerun. JIRA Markdown parsing accepts standard and pasted BDD formats, and the active sample run was reprocessed with 9 acceptance criteria linked to 11 BRD requirements and `PAY-101`.

Validation and review presentation update: evidence warnings are now displayed in Test Cases as `REVIEW REQUIRED` rather than the ambiguous raw `WARNING` label. The Review report presents KPI cards, review queue, approval progress, next action, and status distribution as readable summary points while retaining the underlying validation evidence.

Test case review update: visible case identifiers now use stable sequential numbers (`TC-001`, `TC-002`, ...), while UUIDs remain internal references. Reviewers can assign controlled priority values from the case editor, and approved cases show an approval outcome with any underlying validation note retained.

Live case-module verification: the active persisted run loads as `TC-001` through `TC-057`; approved cases remain attributable and counted separately from cases awaiting review. The Test Cases view displays `APPROVED` for the human review outcome and retains any non-blocking quality warning as a secondary note.

- [ ] Completed: `TASK-002`, `TASK-003`, `TASK-008`, `TASK-009`, `TASK-010`, `TASK-011`, `TASK-012`, `TASK-017`, `TASK-019`, `TASK-020`, `TASK-027`, `TASK-028`, `TASK-029`, `TASK-030`, `TASK-031`, `TASK-033`, `TASK-034`, `TASK-035`, `TASK-036`, `TASK-038`, `TASK-039`, `TASK-040`, `TASK-041`, `TASK-043`, `TASK-044`, `TASK-045`, `TASK-047`, `TASK-048` plus the requested web UI/API vertical slice.
- [ ] In Progress: full contract parity for the original DOCX and structured JIRA JSON adapters, complete 12-gate validation, production RBAC, OCR, review-view formatting, and broader integration/CLI coverage.
- [ ] Not Started: release/UAT activities, performance and cost baselines, security sign-off, operational handover, production deployment hardening, and final CI dependency-audit remediation for the shared environment.

The status list above records the current implementation slice; the individual task sections remain the detailed acceptance contract and must be changed to `[ ] Completed` only when their full original scope is satisfied.

---

## Task Summary & Status Dashboard

- **Total Tasks:** 54
- **Not Started:** 54
- **In Progress:** 0
- **Completed:** 0

---

## 1. Repository and Environment Setup

### TASK-001: Project Directory Structure Initialization
- **Task ID:** TASK-001
- **Task Name:** Project Directory Structure Initialization
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Scaffolding the complete clean-architecture directory layout and package markers according to `spec.md §24`.
- **Description:** Create all domain, application, infrastructure, interface, configuration, test, document, and fixture folders along with empty `__init__.py` files where required.
- **Dependencies:** None
- **Expected Input:** Project folder structure layout from `spec.md §24`.
- **Expected Output:** Created directory structure with all package markers present.
- **Acceptance Criteria:**
  1. All folders listed in `spec.md §24` exist.
  2. Every Python package directory contains an `__init__.py` file.
  3. No source code or extra files exist in `__init__.py` files beyond package markers.
- **Definition of Done:** Directory tree verified; running `python -c "import tcg"` resolves without import errors.

---

### TASK-002: Dependency Specification and Project Configuration (`pyproject.toml`)
- **Task ID:** TASK-002
- **Task Name:** Dependency Specification and Project Configuration (`pyproject.toml`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Configure Python dependencies, tool settings, and project metadata in `pyproject.toml`.
- **Description:** Define project build system, runtime dependencies (`pydantic>=2.7,<3`, `python-docx>=1.1,<2`, `pdfplumber>=0.11,<1`, `openai>=1.30,<2`, `click>=8.1,<9`, `langdetect>=1.0,<2`, `python-magic>=0.4,<1`), dev dependencies (`pytest`, `mypy`, `ruff`, `pip-audit`, `detect-secrets`), and strict tool configurations (`mypy --strict`, `ruff` rules, `pytest`).
- **Dependencies:** TASK-001
- **Expected Input:** Dependency requirements from `plan.md §Phase 1.2`.
- **Expected Output:** Valid `pyproject.toml` file at the workspace root.
- **Acceptance Criteria:**
  1. Runtime and development dependencies are pinned with appropriate bounds.
  2. `mypy` strict mode (`strict = true`) is configured.
  3. `ruff` rule sets (`E`, `F`, `W`, `I`, `UP`, `S`, `B`, `A`) are enabled.
  4. `pip install -e ".[dev]"` installs without version resolution errors.
- **Definition of Done:** `pyproject.toml` created and verified via `pip install -e .`.

---

### TASK-003: Environment Variable Template (`.env.example`) and Git Ignore Setup
- **Task ID:** TASK-003
- **Task Name:** Environment Variable Template (`.env.example`) and Git Ignore Setup
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Configure project environment variables template and repository exclusion rules.
- **Description:** Create `.gitignore` to exclude virtual environments, build artifacts, cache files, secrets, local storage, logs, and `.env`. Create `.env.example` documenting all configuration keys (`TCG_AI_API_KEY`, `TCG_AI_MODEL_NAME`, `TCG_STORAGE_BASE_DIR`, `TCG_AUDIT_LOG_PATH`, etc.) with dummy values.
- **Dependencies:** TASK-001
- **Expected Input:** Environmental variables list from `plan.md §Phase 1.4`.
- **Expected Output:** `.gitignore` and `.env.example` files.
- **Acceptance Criteria:**
  1. `.env.example` documents all required and optional environment variables with comments.
  2. No actual API keys or secrets exist in `.env.example`.
  3. `.gitignore` prevents tracking of `.env`, `storage/`, `*.log`, `*.audit.jsonl`, and `.mypy_cache`.
- **Definition of Done:** Both files created and validated against secrets leak checks.

---

### TASK-004: Pre-Commit Hooks Setup
- **Task ID:** TASK-004
- **Task Name:** Pre-Commit Hooks Setup
- **Status:** [ ] Not Started
- **Priority:** Medium (P1)
- **Objective:** Configure local git hooks for linting, type-checking, and secret detection.
- **Description:** Create `.pre-commit-config.yaml` to execute `ruff check`, `mypy`, and `detect-secrets` on staged files prior to commit.
- **Dependencies:** TASK-002, TASK-003
- **Expected Input:** `plan.md §Phase 1.9` pre-commit configuration.
- **Expected Output:** `.pre-commit-config.yaml` file.
- **Acceptance Criteria:**
  1. Hooks run `ruff` formatting and lint checks on staged `.py` files.
  2. Hooks run `mypy` static type checking on staged `.py` files.
  3. Hooks execute `detect-secrets` scan to block accidental credential commits.
- **Definition of Done:** File created and verified via `pre-commit run --all-files`.

---

## 2. Application Architecture

### TASK-005: Core Domain Enumerations and Value Objects
- **Task ID:** TASK-005
- **Task Name:** Core Domain Enumerations and Value Objects
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement core domain enumerations, immutable models, and common data carriers.
- **Description:** Implement domain enumerations in `src/tcg/domain/models/enums.py` (`SourceType`, `DataClassification`, `ProcessingStatus`, `ExtractionMethod`, `RequirementType`, `NodeType`, `EdgeType`, `PathType`, `LinkType`, `TestType`, `Priority`, `ReviewStatus`, `ValidationStatus`, `FindingSeverity`, `GateType`, `ExportFormat`, `AuditEventType`). Implement source models (`SourceMetadata`, `SourceLocation`, `BoundingBox`), result containers (`ProcessingResult`, `ProcessingError`, `PreflightResult`), flow models (`FlowNode`, `FlowEdge`, `FlowPath`, `AmbiguityWarning`, `FlowDiagram`), and audit models (`AuditEvent`). All domain models must be frozen dataclasses.
- **Dependencies:** TASK-001
- **Expected Input:** Domain model specifications in `spec.md §16`.
- **Expected Output:** Domain models in `src/tcg/domain/models/`.
- **Acceptance Criteria:**
  1. Models use `@dataclass(frozen=True)` for immutability.
  2. Type hints are fully specified without using `Any`.
  3. Domain layer has zero imports from infrastructure or interface modules.
- **Definition of Done:** Files created, passing `mypy --strict`.

---

### TASK-006: Port Protocol Declarations
- **Task ID:** TASK-006
- **Task Name:** Port Protocol Declarations
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Define abstract domain ports using Python `typing.Protocol` for dependency inversion.
- **Description:** Implement port protocol files in `src/tcg/domain/ports/`: `ISourceParser`, `IAIProvider`, `IRunStorage`, `IAuditWriter`, `IExporter`, and `ISensitiveDataScanner` using `@runtime_checkable` protocols.
- **Dependencies:** TASK-005
- **Expected Input:** Port interface specifications in `spec.md §17`.
- **Expected Output:** Interface definitions in `src/tcg/domain/ports/`.
- **Acceptance Criteria:**
  1. All 6 port protocols defined using `typing.Protocol`.
  2. All methods carry strict type annotations and docstrings defining input/output contracts.
  3. No infrastructure imports exist in port definitions.
- **Definition of Done:** Protocols implemented and verified with a unit test checking runtime Protocol conformance.

---

### TASK-007: Composition Root and Interface Dispatch
- **Task ID:** TASK-007
- **Task Name:** Composition Root and Interface Dispatch
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement CLI main entry point and dependency injection composition root.
- **Description:** Implement `src/tcg/interfaces/cli/main.py` using Click. Create the composition root that wires concrete infrastructure instances to domain ports and injects them into application use cases.
- **Dependencies:** TASK-005, TASK-006
- **Expected Input:** Layer responsibilities in `spec.md §1.2` & `§2.2`.
- **Expected Output:** `src/tcg/interfaces/cli/main.py` and command group scaffolding in `src/tcg/interfaces/cli/commands/`.
- **Acceptance Criteria:**
  1. CLI entry point `tcg` is executable.
  2. Dependencies are injected via constructors; no direct instantiation inside domain or application layers.
  3. Invoking `tcg --help` displays available CLI command groups (`run`, `ingest`, `process`, `generate`, `validate`, `review`, `export`, `report`).
- **Definition of Done:** CLI main module created and verified via `tcg --help`.

---

## 3. Configuration Management

### TASK-008: Default Configuration YAML (`config/defaults.yaml`)
- **Task ID:** TASK-008
- **Task Name:** Default Configuration YAML (`config/defaults.yaml`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Provide a baseline YAML file containing default application settings.
- **Description:** Create `config/defaults.yaml` specifying storage paths, intake file limits (50MB for BRD/PDF, 10MB for JIRA), parser configurations, OCR flags, AI parameters, validation thresholds, export settings, and log levels per `plan.md §Phase 1.5`.
- **Dependencies:** TASK-001
- **Expected Input:** Configuration defaults from `plan.md §Phase 1.5` & `spec.md §18.2`.
- **Expected Output:** `config/defaults.yaml` file.
- **Acceptance Criteria:**
  1. Contains default configuration for storage, intake, parsers, OCR, AI, validation, export, language, and logging.
  2. No secrets or production credentials included.
  3. Valid YAML structure.
- **Definition of Done:** File created and parsed successfully by standard YAML loader.

---

### TASK-009: Typed Settings Loader (`tcg/config/settings.py`)
- **Task ID:** TASK-009
- **Task Name:** Typed Settings Loader (`tcg/config/settings.py`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement Pydantic `BaseSettings` configuration loader with strict precedence rules.
- **Description:** Implement `TCGSettings` in `src/tcg/config/settings.py` loading settings in order: environment variables -> user config file -> default config YAML -> built-in defaults. Raise `ConfigurationError` if required secrets or configurations are invalid.
- **Dependencies:** TASK-008
- **Expected Input:** Configuration model specification in `spec.md §18.2`.
- **Expected Output:** `src/tcg/config/settings.py`.
- **Acceptance Criteria:**
  1. Configuration fields use Pydantic models with type validation.
  2. Environment variables override YAML defaults.
  3. Stores API key environment variable name, never raw secrets in settings objects.
- **Definition of Done:** Module implemented and validated with unit tests for setting precedence.

---

### TASK-010: Schema Registry (`tcg/config/schema_registry.py`)
- **Task ID:** TASK-010
- **Task Name:** Schema Registry (`tcg/config/schema_registry.py`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement versioned JSON and CSV schema lookup registry.
- **Description:** Implement `SchemaRegistry` in `src/tcg/config/schema_registry.py` providing `get_schema(version)`, `get_csv_columns(version)`, `is_known_version(version)`, and `current_version()`.
- **Dependencies:** TASK-005
- **Expected Input:** Schema specifications from `spec.md §13.3` & `§13.4`.
- **Expected Output:** `src/tcg/config/schema_registry.py`.
- **Acceptance Criteria:**
  1. Returns JSON Schema structure for version `"1.0"`.
  2. Returns 19 CSV column headers for version `"1.0"`.
  3. Raises `ConfigurationError` when an unknown version is requested.
- **Definition of Done:** Module implemented and unit-tested for schema retrieval.

---

## 4. Logging

### TASK-011: Structured Logging System (`tcg/config/logging_config.py`)
- **Task ID:** TASK-011
- **Task Name:** Structured Logging System (`tcg/config/logging_config.py`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Configure structured JSON and text logging handlers.
- **Description:** Implement `src/tcg/config/logging_config.py` configuring loggers (`tcg`, `tcg.intake`, `tcg.parsing`, etc.). Format output as JSON or text including `timestamp`, `level`, `logger`, `run_id`, `source_id`, and `message`. Ensure secrets and source content are excluded from log outputs.
- **Dependencies:** TASK-009
- **Expected Input:** Logging requirements from `spec.md §15.1`.
- **Expected Output:** `src/tcg/config/logging_config.py`.
- **Acceptance Criteria:**
  1. JSON log records include `timestamp`, `level`, `logger`, `run_id`, `source_id`, `message`.
  2. Operational logging excludes secrets, tokens, API keys, and raw source text.
  3. Log level is configurable via settings.
- **Definition of Done:** Module implemented and tested by capturing log output formats.

---

### TASK-012: Audit Log Writer (`tcg/infrastructure/audit/file_audit_writer.py`)
- **Task ID:** TASK-012
- **Task Name:** Audit Log Writer (`tcg/infrastructure/audit/file_audit_writer.py`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement append-only JSONL audit event recorder implementing `IAuditWriter`.
- **Description:** Implement `FileAuditWriter` in `src/tcg/infrastructure/audit/file_audit_writer.py`. Append `AuditEvent` objects to configured audit JSONL file with file permissions `0o640`. Ensure failures write a critical operational log without raising exceptions to abort core processing. Dual-write security events to security log path.
- **Dependencies:** TASK-005, TASK-006, TASK-011
- **Expected Input:** Audit specifications in `spec.md §15.2`.
- **Expected Output:** `src/tcg/infrastructure/audit/file_audit_writer.py`.
- **Acceptance Criteria:**
  1. Implements `IAuditWriter` protocol.
  2. Writes newline-delimited JSON records.
  3. Prevents log truncation or file overwrites.
  4. Security audit events are routed to both general and security audit paths.
- **Definition of Done:** Implemented and unit-tested for append behavior and file permission compliance.

---

## 5. BRD Processing

### TASK-013: DOCX BRD Document Parser (`DocxBRDParser`)
- **Task ID:** TASK-013
- **Task Name:** DOCX BRD Document Parser (`DocxBRDParser`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Parse Microsoft Word (.docx) BRDs into structured sections, paragraphs, lists, and candidate requirements.
- **Description:** Implement `DocxBRDParser` in `src/tcg/infrastructure/parsers/brd/docx_parser.py` implementing `ISourceParser`. Traverse OOXML structure in document order, tracking heading stacks (`section_path`), extracting candidate requirements matching configurable regex patterns, extracting tables via `TableExtractor`, and identifying boilerplate regions.
- **Dependencies:** TASK-005, TASK-006
- **Expected Input:** DOCX parser requirements in `spec.md §4.2`.
- **Expected Output:** `src/tcg/infrastructure/parsers/brd/docx_parser.py`.
- **Acceptance Criteria:**
  1. Implements `ISourceParser` protocol.
  2. Preserves heading breadcrumb hierarchy (`section_path`) for every paragraph.
  3. Tags paragraphs matching requirement ID regex patterns as candidate requirements.
  4. Returns `BRDExtractionResult` with extracted sections, tables, boilerplate, and confidence score.
- **Definition of Done:** Module implemented and verified against fixture `sample_brd_with_ids.docx`.

---

### TASK-014: PDF BRD Document Parser (`PdfBRDParser`)
- **Task ID:** TASK-014
- **Task Name:** PDF BRD Document Parser (`PdfBRDParser`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Parse searchable and text-native PDF BRDs into structured extracted content.
- **Description:** Implement `PdfBRDParser` in `src/tcg/infrastructure/parsers/brd/pdf_brd_parser.py` implementing `ISourceParser`. Detect text-native vs. image-only PDF. Reconstruct reading order using bounding-box spatial clustering. Tag text blocks with `ORDERING_UNCERTAIN` when spatial ordering is ambiguous. Delegate to `OCRProcessor` if image-only and OCR enabled; otherwise return `REQUIRES_OCR_OR_MANUAL_REVIEW`.
- **Dependencies:** TASK-005, TASK-006
- **Expected Input:** PDF BRD requirements in `spec.md §4.3`.
- **Expected Output:** `src/tcg/infrastructure/parsers/brd/pdf_brd_parser.py`.
- **Acceptance Criteria:**
  1. Implements `ISourceParser` protocol.
  2. Correctly differentiates text-native vs scanned image PDFs.
  3. Reconstructs text streams with page number and bounding-box coordinates.
  4. Identifies repeat headers/footers as boilerplate.
- **Definition of Done:** Module implemented and verified against `sample_brd_text_native.pdf`.

---

## 6. JIRA User Story Processing

### TASK-015: JIRA JSON Import Parser (`JiraJsonImportParser`)
- **Task ID:** TASK-015
- **Task Name:** JIRA JSON Import Parser (`JiraJsonImportParser`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Extract user stories, issue fields, and metadata from structured JIRA JSON exports.
- **Description:** Implement `JiraJsonImportParser` in `src/tcg/infrastructure/parsers/jira/json_import_parser.py` implementing `ISourceParser`. Parse JIRA issue keys, summaries, Atlassian Document Format (ADF) descriptions, priorities, statuses, labels, components, and linked issues. Use configurable `jira_acceptance_criteria_field` custom field key.
- **Dependencies:** TASK-005, TASK-006, TASK-009
- **Expected Input:** JIRA parser specification in `spec.md §5`.
- **Expected Output:** `src/tcg/infrastructure/parsers/jira/json_import_parser.py`.
- **Acceptance Criteria:**
  1. Implements `ISourceParser` protocol.
  2. Converts ADF description structures to plain text.
  3. Maps JIRA issue fields to `JiraStory` domain models.
  4. Flag missing required fields as warnings in extraction result.
- **Definition of Done:** Implemented and tested against fixture `stories_with_criteria.json`.

---

### TASK-016: Acceptance Criteria Decomposer and Conflict Detector
- **Task ID:** TASK-016
- **Task Name:** Acceptance Criteria Decomposer and Conflict Detector
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Split acceptance criteria text into atomic units and detect conflicts with story descriptions.
- **Description:** Implement acceptance criteria splitting (by Given/When/Then, numbered items, or line breaks) inside `JiraJsonImportParser`. Assign internal IDs `{story_key}-AC-{n}` with `id_origin: SYSTEM_GENERATED` when missing. Compare criteria statements against story descriptions to flag explicit contradictions as `RequirementConflict` instances.
- **Dependencies:** TASK-015
- **Expected Input:** Acceptance criteria processing in `spec.md §5.3`.
- **Expected Output:** Enhanced `JiraJsonImportParser` handling criteria decomposition.
- **Acceptance Criteria:**
  1. Converts raw criteria text into individual `AcceptanceCriterion` objects.
  2. Assigns deterministic internal IDs for unnumbered criteria.
  3. Flags contradiction keywords between description and criteria as `RequirementConflict`.
- **Definition of Done:** Unit-tested with fixture `stories_with_conflict.json`.

---

## 7. PDF Processing

### TASK-017: Preflight File Integrity and MIME Validator (`FileValidator`)
- **Task ID:** TASK-017
- **Task Name:** Preflight File Integrity and MIME Validator (`FileValidator`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Perform 11 mandatory preflight safety and format validation checks on input files prior to ingestion.
- **Description:** Implement `FileValidator` in `src/tcg/infrastructure/security/file_validator.py`. Run checks: authorization, file existence, size check, magic-byte MIME detection, format support, SHA-256 checksum, duplicate identity check, password-protection check, corruption detection, language detection (`langdetect`), and required metadata check.
- **Dependencies:** TASK-005, TASK-009
- **Expected Input:** Preflight validation sequence in `spec.md §3.2`.
- **Expected Output:** `src/tcg/infrastructure/security/file_validator.py`.
- **Acceptance Criteria:**
  1. Rejects files exceeding size limits (`max_file_size_bytes`).
  2. Rejects password-protected PDFs without reading full content.
  3. Verifies magic bytes rather than trusting file extensions alone.
  4. Flags non-English document samples per baseline setting.
- **Definition of Done:** Implemented and unit-tested against invalid, corrupted, encrypted, and spoofed file fixtures.

---

### TASK-018: OCR Image Processor Adapter (`OCRProcessor`)
- **Task ID:** TASK-018
- **Task Name:** OCR Image Processor Adapter (`OCRProcessor`)
- **Status:** [ ] Not Started
- **Priority:** Medium (P1)
- **Objective:** Provide a gated OCR processing adapter for scanned image-only PDF documents.
- **Description:** Implement `OCRProcessor` in `src/tcg/infrastructure/extraction/ocr_processor.py`. Evaluate `ocr.enabled` setting; raise `ConfigurationError` if disabled. Enforce `max_image_size_bytes` limits. Execute configured OCR engine, tagging all output with `extraction_method: OCR` and confidence metrics.
- **Dependencies:** TASK-005, TASK-009
- **Expected Input:** OCR engine specification in `spec.md §7.4`.
- **Expected Output:** `src/tcg/infrastructure/extraction/ocr_processor.py`.
- **Acceptance Criteria:**
  1. Respects `ocr.enabled` flag; aborts cleanly when disabled.
  2. Limits image size before passing data to OCR engine.
  3. Tags extracted text blocks with `extraction_method: OCR`.
- **Definition of Done:** Implemented and unit-tested with mock OCR engine.

---

## 8. Flow Diagram Processing

### TASK-019: Vector and Layout Diagram Parser (`PdfFlowDiagramParser`)
- **Task ID:** TASK-019
- **Task Name:** Vector and Layout Diagram Parser (`PdfFlowDiagramParser`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Extract vector shapes, connectors, text labels, and annotations from flow diagram PDFs.
- **Description:** Implement `PdfFlowDiagramParser` in `src/tcg/infrastructure/parsers/flow/pdf_flow_parser.py` implementing `ISourceParser`. Extract graphics content streams, bounding boxes, labels, and line paths from text-native PDF pages. Identify flow pages using heuristic thresholds.
- **Dependencies:** TASK-005, TASK-006
- **Expected Input:** Flow diagram parsing specification in `spec.md §6.2`.
- **Expected Output:** `src/tcg/infrastructure/parsers/flow/pdf_flow_parser.py`.
- **Acceptance Criteria:**
  1. Implements `ISourceParser` protocol.
  2. Extracts visual elements (rectangles, diamonds, arrows, text labels) with spatial coordinates.
  3. Delegates image-only diagram pages to OCR or flags `REQUIRES_OCR_OR_MANUAL_REVIEW`.
- **Definition of Done:** Implemented and tested against fixture `simple_linear_flow.pdf`.

---

### TASK-020: Diagram Graph Constructor and Path Enumerator (`DiagramExtractor`)
- **Task ID:** TASK-020
- **Task Name:** Diagram Graph Constructor and Path Enumerator (`DiagramExtractor`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Convert visual flow elements into a directed graph and enumerate all executable flow paths.
- **Description:** Implement `DiagramExtractor` in `src/tcg/infrastructure/extraction/diagram_extractor.py`. Perform connector endpoint proximity matching to form `FlowNode` and `FlowEdge` objects. Detect `DANGLING_NODE` and `INCOMPLETE_DECISION` conditions. Perform depth-limited DFS path enumeration to construct `FlowPath` objects for main, alternate, and error branches. Tag inferred nodes/edges with `is_inferred: True`.
- **Dependencies:** TASK-005, TASK-019
- **Expected Input:** Graph construction rules in `spec.md §6.3` & `§6.4`.
- **Expected Output:** `src/tcg/infrastructure/extraction/diagram_extractor.py`.
- **Acceptance Criteria:**
  1. Builds directed graph with typed nodes (`START`, `ACTIVITY`, `DECISION`, `END`).
  2. Correctly flags ambiguous connectors as `AmbiguityWarning`.
  3. Enumerates all complete paths from start to end nodes, identifying alternate and error branches.
  4. Prevents infinite recursion on loops using depth limits.
- **Definition of Done:** Unit-tested against branching and looping diagram fixtures (`branching_flow.pdf`, `loop_flow.pdf`).

---

## 9. Requirement Extraction

### TASK-021: Text Block and Bounding Box Extractor (`TextExtractor`)
- **Task ID:** TASK-021
- **Task Name:** Text Block and Bounding Box Extractor (`TextExtractor`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Extract format-agnostic, spatial text blocks with layout provenance from raw document content.
- **Description:** Implement `TextExtractor` in `src/tcg/infrastructure/extraction/text_extractor.py`. Convert PDF/DOCX extraction outputs into ordered `TextBlock` objects carrying text, block type, page number, section breadcrumb, bounding box coordinates, extraction method, and confidence score.
- **Dependencies:** TASK-005
- **Expected Input:** Text extraction specification in `spec.md §7.2`.
- **Expected Output:** `src/tcg/infrastructure/extraction/text_extractor.py`.
- **Acceptance Criteria:**
  1. Reconstructs text blocks preserving reading order.
  2. Attaches spatial bounding boxes when available.
  3. Assigns confidence metrics based on extraction method.
- **Definition of Done:** Module implemented and unit-tested with multi-page text blocks.

---

### TASK-022: Table Structure and Cell Merging Extractor (`TableExtractor`)
- **Task ID:** TASK-022
- **Task Name:** Table Structure and Cell Merging Extractor (`TableExtractor`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Extract structural tables preserving row/column relationships and merged cell spans.
- **Description:** Implement `TableExtractor` in `src/tcg/infrastructure/extraction/table_extractor.py`. Process DOCX and PDF table layouts into `Table` objects containing `TableCell` matrices. Handle `row_span` and `col_span` merged cells by attaching `merged_from` position references without flattening grid data into plain text.
- **Dependencies:** TASK-005
- **Expected Input:** Table extraction specification in `spec.md §7.3`.
- **Expected Output:** `src/tcg/infrastructure/extraction/table_extractor.py`.
- **Acceptance Criteria:**
  1. Preserves row and column index positioning.
  2. Resolves merged cells with explicit span properties.
  3. Generates structured `Table` domain representation.
- **Definition of Done:** Unit-tested with complex merged-header table fixtures.

---

## 10. Requirement Normalization

### TASK-023: Canonical Requirement Identifier & Text Normalizer
- **Task ID:** TASK-023
- **Task Name:** Canonical Requirement Identifier & Text Normalizer
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement Steps 1 & 2 of the requirement normalization pipeline.
- **Description:** Implement identifier assignment and text normalization in `src/tcg/infrastructure/normalization/requirement_normalizer.py`. Assign UUID `requirement_id`. Preserves explicit business IDs (`business_id`, `id_origin: BUSINESS`) or generate deterministic fallback IDs (`{source_id}-REQ-{sha256[:8]}`, `id_origin: SYSTEM_GENERATED`). Perform whitespace and Unicode normalization while preserving `original_text` verbatim.
- **Dependencies:** TASK-005
- **Expected Input:** Normalization rules Steps 1 & 2 in `spec.md §8.2`.
- **Expected Output:** Normalization module implementation for Steps 1 & 2.
- **Acceptance Criteria:**
  1. Preserves original business requirement IDs.
  2. Generates deterministic SHA-256 fallback IDs for unnumbered items.
  3. Preserves `original_text` unmodified alongside `normalized_text`.
- **Definition of Done:** Implemented and unit-tested for identifier stability.

---

### TASK-024: Requirement Deduplication, Candidate Linking, and Gap Identification (`RequirementNormalizer`)
- **Task ID:** TASK-024
- **Task Name:** Requirement Deduplication, Candidate Linking, and Gap Identification (`RequirementNormalizer`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Complete Steps 3, 4, and 5 of the requirement normalization pipeline.
- **Description:** Implement deduplication (Step 3: exact match -> `SUPERSEDED`; TF-IDF cosine similarity above threshold -> `NEAR_DUPLICATE`), cross-source linking (Step 4: create `TraceLink` between BRD, JIRA, and Flow items), and gap identification (Step 5: flag `GAP: BRD_NO_STORY`, `GAP: STORY_NO_CRITERIA`, `GAP: FLOW_NO_REQUIREMENT`). Return `NormalizationResult` containing `NormalizedRequirement` list and `NormalizationIssue` list.
- **Dependencies:** TASK-023
- **Expected Input:** Normalization rules Steps 3–5 in `spec.md §8.2` & `§8.3`.
- **Expected Output:** `src/tcg/infrastructure/normalization/requirement_normalizer.py`.
- **Acceptance Criteria:**
  1. Flags near-duplicate requirements above similarity threshold as reviewable issues.
  2. Creates cross-source candidate links.
  3. Emits `NormalizationIssue` instances for unlinked stories, missing criteria, or orphan flow paths.
- **Definition of Done:** Full normalizer implemented and verified with multi-source integration test.

---

## 11. Requirement Traceability

### TASK-025: Traceability Graph Constructor (`TraceabilityService`)
- **Task ID:** TASK-025
- **Task Name:** Traceability Graph Constructor (`TraceabilityService`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Construct an adjacency-list traceability graph linking requirements, stories, criteria, flow nodes, and test cases.
- **Description:** Implement `TraceabilityService` in `src/tcg/domain/services/traceability_service.py`. Implement `build_graph()` to create an in-memory graph of `TraceLink` objects. Support bi-directional traversal between requirements and generated test cases.
- **Dependencies:** TASK-005, TASK-024
- **Expected Input:** Traceability graph specification in `spec.md §9.1` & `§9.2`.
- **Expected Output:** `src/tcg/domain/services/traceability_service.py`.
- **Acceptance Criteria:**
  1. Represents many-to-many links between sources and test cases.
  2. Supports adjacency lookup by source entity ID or test case ID.
  3. Exportable to JSON structure.
- **Definition of Done:** Implemented and unit-tested for graph building and traversal.

---

### TASK-026: Source Reference Resolver and Change Impact Engine
- **Task ID:** TASK-026
- **Task Name:** Source Reference Resolver and Change Impact Engine
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Resolve source references against active registries and detect change impacts on updated sources.
- **Description:** Implement `resolve_reference()` and `detect_change_impact()` in `TraceabilityService`. Resolve references to `RESOLVED`, `STALE`, `BROKEN`, or `CANDIDATE`. On source checksum update, identify all impacted test cases, flag references as `STALE`/`BROKEN`, and queue affected cases for re-review (`NEEDS_REREVIEW`).
- **Dependencies:** TASK-025
- **Expected Input:** Reference resolution & change impact logic in `spec.md §9.3` & `§9.5`.
- **Expected Output:** Enhanced `TraceabilityService` with resolution and impact analysis.
- **Acceptance Criteria:**
  1. Returns `RESOLVED` for valid, matching source locations.
  2. Flags references as `BROKEN` if source ID or location is missing.
  3. Transitions test case status to `NEEDS_REREVIEW` when underlying source checksum changes.
- **Definition of Done:** Unit-tested with simulated source updates and broken location lookups.

---

## 12. AI Prompt Management

### TASK-027: Security-Hardened Versioned Prompt Template (`config/prompt_templates/generate_v1.0.txt`)
- **Task ID:** TASK-027
- **Task Name:** Security-Hardened Versioned Prompt Template (`config/prompt_templates/generate_v1.0.txt`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Create version 1.0 of the prompt template with explicit structural section boundaries and injection defense rules.
- **Description:** Create `config/prompt_templates/generate_v1.0.txt` featuring four distinct logical sections: system instructions (version identifier `generate_v1.0`, output schema version `1.0`), explicit structural separation marker (`=== EVIDENCE STARTS BELOW ===`), evidence context placeholders, and JSON output contract rules per `spec.md §11.3`.
- **Dependencies:** TASK-010
- **Expected Input:** Prompt engineering requirements in `spec.md §11.3`.
- **Expected Output:** `config/prompt_templates/generate_v1.0.txt`.
- **Acceptance Criteria:**
  1. Contains instruction set version `generate_v1.0` and schema version `1.0`.
  2. Embeds rigid structural separation boundary around untrusted evidence.
  3. Formats expected output structure as JSON Schema rules.
  4. Contains explicit prohibitions against inventing requirements or uncited expected outcomes.
- **Definition of Done:** File created and version registered in `SchemaRegistry`.

---

### TASK-028: Prompt Builder and Instruction Injector (`PromptBuilder`)
- **Task ID:** TASK-028
- **Task Name:** Prompt Builder and Instruction Injector (`PromptBuilder`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Construct final AI generation prompts from versioned templates and assembled evidence packages.
- **Description:** Implement `PromptBuilder` in `src/tcg/infrastructure/ai/prompt_builder.py`. Load template files dynamically by version string. Substitute sanitized evidence content, requirement text, and JSON schema constraints into template placeholders. Record prompt version string in generation metadata.
- **Dependencies:** TASK-027
- **Expected Input:** Prompt builder specification in `spec.md §11.3`.
- **Expected Output:** `src/tcg/infrastructure/ai/prompt_builder.py`.
- **Acceptance Criteria:**
  1. Dynamically loads templates from `config/prompt_templates/`.
  2. Raises `ConfigurationError` if template version does not exist.
  3. Prevents prompt log output from containing raw text.
- **Definition of Done:** Implemented and unit-tested for prompt assembly.

---

### TASK-029: OpenAI API Adapter with Retry & Rate-Limit Handling (`OpenAIAdapter`)
- **Task ID:** TASK-029
- **Task Name:** OpenAI API Adapter with Retry & Rate-Limit Handling (`OpenAIAdapter`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement `IAIProvider` port adapter for OpenAI API with retry policy and secret isolation.
- **Description:** Implement `OpenAIAdapter` in `src/tcg/infrastructure/ai/openai_adapter.py`. Read API key from environment variable at call time (`os.environ.get()`). Enforce `temperature` (default `0.0`), `max_tokens`, and `timeout_seconds`. Implement exponential backoff retry for HTTP 429/503/504 errors. Return `ProcessingResult` with raw response or retryable error.
- **Dependencies:** TASK-005, TASK-006, TASK-009
- **Expected Input:** AI provider spec in `spec.md §11.4` & `§17.2`.
- **Expected Output:** `src/tcg/infrastructure/ai/openai_adapter.py`.
- **Acceptance Criteria:**
  1. Implements `IAIProvider` protocol.
  2. Reads API key strictly from environment variables without storing key in instance state or logs.
  3. Uses exponential backoff retries on rate limits (429) or transient server errors (503).
  4. Returns `AIRawResponse` object carrying token usage counts.
- **Definition of Done:** Implemented and unit-tested using mocked OpenAI client responses.

---

## 13. Test Scenario Generation

### TASK-030: Scenario Plan Applicability Evaluator (7-Class Rules)
- **Task ID:** TASK-030
- **Task Name:** Scenario Plan Applicability Evaluator (7-Class Rules)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Evaluate applicability for all 7 mandatory scenario classes for each requirement.
- **Description:** Implement scenario class evaluation rules in `src/tcg/domain/services/domain_validator.py` (`spec.md §10.2`). Evaluate Positive, Negative, Boundary, Validation, Exception, Integration, and End-to-End scenario classes against source evidence. Record status (`APPLICABLE`, `EXCLUDED`, `UNRESOLVED`) and evidence rationale for each class in `ScenarioPlan`.
- **Dependencies:** TASK-005, TASK-024
- **Expected Input:** Scenario classification rules in `spec.md §10.2` & `§10.3`.
- **Expected Output:** `ScenarioPlan` evaluator in `DomainValidationService`.
- **Acceptance Criteria:**
  1. Positive class is applicable whenever testable behavior exists.
  2. Boundary class is `APPLICABLE` only when explicit limit values exist in source evidence.
  3. Negative class is `APPLICABLE` only when rejection or error rules exist.
  4. Records explicit exclusion rationale for excluded classes.
- **Definition of Done:** Unit-tested with requirements exercising all 7 scenario classes.

---

### TASK-031: Context Budget Manager, Trimming & Redactor (`ContextAssembler`)
- **Task ID:** TASK-031
- **Task Name:** Context Budget Manager, Trimming & Redactor (`ContextAssembler`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Assemble minimal evidence context respecting token budgets and redacting sensitive data.
- **Description:** Implement `ContextAssembler` in `src/tcg/infrastructure/ai/context_assembler.py` and `Redactor` in `src/tcg/infrastructure/security/redactor.py`. Assemble requirement statements, criteria, boundary values, and step labels within `ai.context_budget_per_requirement` limit. Trim lower-priority context if over budget and record in `omitted_refs`. Apply `Redactor` to sanitize tokens/card numbers and block prompt injection phrases.
- **Dependencies:** TASK-005, TASK-009, TASK-030
- **Expected Input:** Context assembler rules in `spec.md §11.2` & security rules in `§19.3`.
- **Expected Output:** `src/tcg/infrastructure/ai/context_assembler.py` and `src/tcg/infrastructure/security/redactor.py`.
- **Acceptance Criteria:**
  1. Enforces context token budget limit.
  2. Redacts API keys, card numbers, and bearer tokens replacing with `[REDACTED]`.
  3. Replaces prompt injection blocklist phrases with `[CONTENT_REDACTED_INJECTION_RISK]`.
  4. Records omitted references in `EvidencePackage.omitted_refs`.
- **Definition of Done:** Unit-tested for budget enforcement, redaction, and prompt injection mitigation.

---

## 14. Test Case Generation

### TASK-032: AI Response Structuring Parser & Citation Verifier (`AIResponseParser`)
- **Task ID:** TASK-032
- **Task Name:** AI Response Structuring Parser & Citation Verifier (`AIResponseParser`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Parse raw AI JSON responses into structured case drafts and verify cited source references.
- **Description:** Implement `AIResponseParser` in `src/tcg/infrastructure/ai/response_parser.py`. Parse JSON string against schema. Handle malformed JSON (`GENERATION_FAILED`), truncation, and model refusal (`GENERATION_REFUSED`). Cross-check model-cited source references against `EvidencePackage.included_items`; tag unverified references as `UNVERIFIED_CITATION`. Extract `assumptions` and `open_questions` into separate fields.
- **Dependencies:** TASK-005, TASK-010, TASK-031
- **Expected Input:** Response parser rules in `spec.md §11.5`.
- **Expected Output:** `src/tcg/infrastructure/ai/response_parser.py`.
- **Acceptance Criteria:**
  1. Parses raw JSON responses into `TestCaseDraft` objects.
  2. Handles malformed JSON, truncation, and refusals without crashing.
  3. Tags citations absent from the evidence package as `UNVERIFIED_CITATION`.
  4. Keeps assumptions and open questions separate from test steps.
- **Definition of Done:** Unit-tested against 5 pre-recorded AI response fixtures (`valid_response.json`, `malformed_json_response.txt`, `truncated_response.txt`, `refused_response.json`, `unverified_citation_response.json`).

---

### TASK-033: Draft-to-TestCase Mapper & Priority Derivation Engine
- **Task ID:** TASK-033
- **Task Name:** Draft-to-TestCase Mapper & Priority Derivation Engine
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Map test case drafts into schema-validated `TestCase` domain objects and derive test priorities.
- **Description:** Implement draft mapping in `src/tcg/application/use_cases/generate_test_cases.py` and priority derivation in `DomainValidationService`. Assign UUID `test_case_id`, `schema_version: "1.0"`, `review_status: DRAFT`, `validation_status: FAILED`. Derive priority from source priority fields; if evidence is lacking, assign `Priority.UNKNOWN` with `priority_rationale`. Populate `jira_story_id_na_reason` when JIRA ID is absent.
- **Dependencies:** TASK-005, TASK-010, TASK-032
- **Expected Input:** Draft mapping rules & priority derivation in `spec.md §10.5` & `§16.4`.
- **Expected Output:** Domain mapping implementation in `generate_test_cases.py`.
- **Acceptance Criteria:**
  1. Assigns unique UUID for `test_case_id`.
  2. Defaults `review_status` to `DRAFT`.
  3. Derives `Priority.UNKNOWN` when source evidence lacks priority signals.
  4. Attaches full `GenerationMetadata` (model, prompt version, schema version, source versions).
- **Definition of Done:** Unit-tested for complete `TestCase` instantiation and metadata binding.

---

### TASK-034: Run State & Test Case Persistence Layer (`FileRunStorage`)
- **Task ID:** TASK-034
- **Task Name:** Run State & Test Case Persistence Layer (`FileRunStorage`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement file-system persistence layer for run metadata, sources, requirements, and test cases implementing `IRunStorage`.
- **Description:** Complete `FileRunStorage` in `src/tcg/infrastructure/storage/file_storage.py`. Implement JSON persistence under `{storage.base_dir}/{run_id}/` for runs, sources, extraction results, normalized requirements, trace graphs, and test cases. Implement filtering by review status, validation status, requirement ID, story ID, and test type.
- **Dependencies:** TASK-005, TASK-006, TASK-033
- **Expected Input:** Storage interface specifications in `spec.md §17.3`.
- **Expected Output:** `src/tcg/infrastructure/storage/file_storage.py`.
- **Acceptance Criteria:**
  1. Implements `IRunStorage` protocol completely.
  2. Uses `pathlib.Path` safely without raw string concatenations.
  3. Supports querying test cases with `TestCaseFilter`.
  4. Confirms existing IDs on update to prevent duplicate records.
- **Definition of Done:** Implemented and unit-tested for CRUD operations and filtering.

---

### TASK-035: Test Case Generation Orchestrator Use Case (`GenerateTestCasesUseCase`)
- **Task ID:** TASK-035
- **Task Name:** Test Case Generation Orchestrator Use Case (`GenerateTestCasesUseCase`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Orchestrate the complete end-to-end AI test case generation workflow.
- **Description:** Implement `GenerateTestCasesUseCase` in `src/tcg/application/use_cases/generate_test_cases.py`. Coordinate domain validation, context assembly, prompt construction, AI provider call (with retry), response parsing, draft mapping, and storage persistence. Support partial batch success where failures in one requirement do not abort others. Emit generation audit events.
- **Dependencies:** TASK-028, TASK-029, TASK-031, TASK-032, TASK-033, TASK-034
- **Expected Input:** Generation workflow rules in `prd.md §11` & `spec.md §1.3`.
- **Expected Output:** `src/tcg/application/use_cases/generate_test_cases.py` and CLI `tcg generate` command.
- **Acceptance Criteria:**
  1. Generates test cases scoped by project run, requirement set, or story ID.
  2. Preserves partial success across batch requirement processing.
  3. Persists generated cases with status `DRAFT`.
  4. Records `GENERATION_COMPLETED` audit events.
- **Definition of Done:** Implemented and verified with pipeline integration test using mock AI provider.

---

## 15. Test Case Validation

### TASK-036: Sensitive Data Scanner (`SensitiveDataScanner`)
- **Task ID:** TASK-036
- **Task Name:** Sensitive Data Scanner (`SensitiveDataScanner`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement object-graph scanning for API keys, credentials, card numbers, and PII patterns implementing `ISensitiveDataScanner`.
- **Description:** Implement `SensitiveDataScanner` in `src/tcg/infrastructure/security/sensitive_scanner.py`. Recursively scan all string fields of any dataclass or dict. Detect API key prefixes (`sk-`, `Bearer `, `ghp_`, `eyJ`), Luhn-valid synthetic credit card numbers, password assignments (`password=`), and configured sensitive patterns. Return `ScanResult` containing field paths, omitting matched secret values.
- **Dependencies:** TASK-005, TASK-006, TASK-009
- **Expected Input:** Security gate rules in `spec.md §12.3` & `§19.4`.
- **Expected Output:** `src/tcg/infrastructure/security/sensitive_scanner.py`.
- **Acceptance Criteria:**
  1. Implements `ISensitiveDataScanner` protocol.
  2. Detects API keys, bearer tokens, card numbers, and credentials across all string fields.
  3. Returns field location without logging or returning raw matched secret values.
- **Definition of Done:** Implemented and unit-tested against synthetic secret patterns.

---

### TASK-037: 12-Gate Test Case Validation Pipeline (`ValidateTestCasesUseCase`)
- **Task ID:** TASK-037
- **Task Name:** 12-Gate Test Case Validation Pipeline (`ValidateTestCasesUseCase`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement the 12 sequential validation gates and validation orchestrator use case.
- **Description:** Implement validation gates (Input, Extraction, Identity, Security, Schema, Traceability, Evidence, Coverage, Consistency, Duplication, Audit, Review) in `src/tcg/application/use_cases/validate_test_cases.py` per `spec.md §12.2` & `§12.3`. Execute Security gate before Schema gate. BLOCKING findings set `ValidationStatus.FAILED`/`BLOCKED` and block export; WARNING findings flag issues while allowing `NEEDS_REVIEW` transition. Generate `ValidationReport`.
- **Dependencies:** TASK-025, TASK-034, TASK-036
- **Expected Input:** Validation gate specifications in `spec.md §12`.
- **Expected Output:** `src/tcg/application/use_cases/validate_test_cases.py` and CLI `tcg validate` command.
- **Acceptance Criteria:**
  1. Evaluates all 12 gates in documented sequential order.
  2. Security gate blocks cases containing sensitive data and sets `SECURITY_BLOCKED`.
  3. Traceability gate blocks cases with broken source references.
  4. Cases passing all blocking gates transition from `DRAFT` to `NEEDS_REVIEW`.
- **Definition of Done:** Implemented and unit-tested with 36+ test cases (passing, failing, warning for each gate).

---

## 16. Duplicate Detection

### TASK-038: Test Case Fingerprinting & Deduplication Service (`DeduplicationService`)
- **Task ID:** TASK-038
- **Task Name:** Test Case Fingerprinting & Deduplication Service (`DeduplicationService`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Detect duplicate and near-duplicate test cases using semantic hashing and text similarity.
- **Description:** Implement `DeduplicationService` in `src/tcg/domain/services/deduplication_service.py`. Compute case fingerprint hash: `sha256(normalized_scenario + test_type + requirement_id)`. Exact match -> flag as `DUPLICATE`. Text similarity above `validation.duplication_similarity_threshold` -> flag as `NEAR_DUPLICATE` warning.
- **Dependencies:** TASK-005, TASK-009
- **Expected Input:** Duplication gate specification in `spec.md §12.3` (Gate 10).
- **Expected Output:** `src/tcg/domain/services/deduplication_service.py`.
- **Acceptance Criteria:**
  1. Generates deterministic SHA-256 case fingerprints.
  2. Flags exact duplicates across a generation run.
  3. Emits near-duplicate warnings based on configurable similarity thresholds.
- **Definition of Done:** Implemented and unit-tested for duplicate identification.

---

## 17. Coverage Analysis

### TASK-039: Coverage Metric Calculation Engine (`CoverageService`)
- **Task ID:** TASK-039
- **Task Name:** Coverage Metric Calculation Engine (`CoverageService`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Calculate requirement, story, criteria, and flow path coverage metrics.
- **Description:** Implement `CoverageService` in `src/tcg/domain/services/coverage_service.py`. Calculate `CoverageRecord` for each requirement and entity (`spec.md §9.4`). Track applicable vs. covered vs. excluded vs. unresolved scenario classes. Compute coverage percentages and identify orphan requirements (entities with 0 test cases).
- **Dependencies:** TASK-005, TASK-025, TASK-030
- **Expected Input:** Coverage computation in `spec.md §9.4`.
- **Expected Output:** `src/tcg/domain/services/coverage_service.py`.
- **Acceptance Criteria:**
  1. Computes coverage percentages: `covered / (covered + uncovered applicable)`.
  2. Explicitly identifies orphan requirements with zero test coverage.
  3. Tracks whether an entity has at least one approved test case.
- **Definition of Done:** Implemented and unit-tested for coverage math accuracy.

---

## 18. Output Generation

### TASK-040: Machine-Readable JSON Exporter (`JSONExporter`)
- **Task ID:** TASK-040
- **Task Name:** Machine-Readable JSON Exporter (`JSONExporter`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Export validated test cases to schema-conformant JSON files implementing `IExporter`.
- **Description:** Implement `JSONExporter` in `src/tcg/infrastructure/export/json_exporter.py`. Validate each case against `SchemaRegistry.get_schema("1.0")`. Rescan object with `ISensitiveDataScanner` before export. Apply `require_approved_for_export` policy filter. Redact source excerpts if `config.redact_source_excerpts` is true. Emit `EXPORT_COMPLETED` audit event.
- **Dependencies:** TASK-005, TASK-006, TASK-010, TASK-036
- **Expected Input:** JSON export rules in `spec.md §13.3` & `§14.3`.
- **Expected Output:** `src/tcg/infrastructure/export/json_exporter.py`.
- **Acceptance Criteria:**
  1. Implements `IExporter` protocol for `ExportFormat.JSON`.
  2. Output validates strictly against JSON Schema v1.0.
  3. Respects export approval policies.
  4. Rescans content for sensitive data prior to disk output.
- **Definition of Done:** Implemented and unit-tested against exported JSON validation.

---

### TASK-041: Tabular CSV Exporter (`CSVExporter`)
- **Task ID:** TASK-041
- **Task Name:** Tabular CSV Exporter (`CSVExporter`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Export test cases to 19-column CSV format with UTF-8 BOM encoding implementing `IExporter`.
- **Description:** Implement `CSVExporter` in `src/tcg/infrastructure/export/csv_exporter.py`. Write 19-column header defined in `spec.md §13.4`. Serialize nested lists (`test_steps`, `preconditions`) as JSON-encoded strings. Format `source_references` as pipe-separated display strings. Use `utf-8-sig` encoding for Excel compatibility. Apply scanner and approval filters.
- **Dependencies:** TASK-005, TASK-006, TASK-010, TASK-036
- **Expected Input:** CSV export rules in `spec.md §13.4` & `§14.4`.
- **Expected Output:** `src/tcg/infrastructure/export/csv_exporter.py`.
- **Acceptance Criteria:**
  1. Implements `IExporter` protocol for `ExportFormat.CSV`.
  2. Generates exactly 19 columns in specified order.
  3. Writes file with UTF-8 BOM (`utf-8-sig`) encoding.
  4. Encodes nested lists safely inside CSV cells.
- **Definition of Done:** Implemented and unit-tested by opening CSV output with standard CSV reader.

---

### TASK-042: Markdown Review View Generator (`OutputFormatter`)
- **Task ID:** TASK-042
- **Task Name:** Markdown Review View Generator (`OutputFormatter`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Generate human-readable Markdown review documents displaying test cases alongside source evidence.
- **Description:** Implement `OutputFormatter` in `src/tcg/infrastructure/export/output_formatter.py`. Format test cases into Markdown documents with YAML front matter per `spec.md §13.2`. Display metadata tables, precondition lists, step tables, source evidence citations, assumptions, and validation warnings. Hide sensitive evidence based on access policy.
- **Dependencies:** TASK-005, TASK-033
- **Expected Input:** Markdown review view specification in `spec.md §13.2`.
- **Expected Output:** `src/tcg/infrastructure/export/output_formatter.py`.
- **Acceptance Criteria:**
  1. Formats test cases into readable Markdown with YAML front matter.
  2. Formats steps into Markdown tables (`Step | Action | Expected Result`).
  3. Clearly separates source evidence from assumptions and open questions.
- **Definition of Done:** Implemented and unit-tested for Markdown rendering fidelity.

---

### TASK-043: Multi-View Reporting Suite (`GenerateReportUseCase`)
- **Task ID:** TASK-043
- **Task Name:** Multi-View Reporting Suite (`GenerateReportUseCase`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement the six mandatory project reporting views and reporting use case.
- **Description:** Implement `GenerateReportUseCase` in `src/tcg/application/use_cases/generate_report.py`. Support report types: `GenerationSummaryReport`, `TraceabilityMatrix`, `CoverageReport`, `QualityReport`, `ReviewReport`, and `ChangeImpactReport` per `spec.md §14.2`. Format reports as Markdown tables and JSON objects.
- **Dependencies:** TASK-025, TASK-037, TASK-039
- **Expected Input:** Report specifications in `spec.md §14.2`.
- **Expected Output:** `src/tcg/application/use_cases/generate_report.py` and CLI `tcg report` command.
- **Acceptance Criteria:**
  1. Generates all 6 mandatory report types.
  2. `TraceabilityMatrix` lists orphan requirements separately.
  3. `CoverageReport` details coverage percentages across scenario classes.
  4. Exportable as JSON or Markdown.
- **Definition of Done:** Implemented and verified by generating all 6 reports from test run data.

---

## 19. Unit Testing

### TASK-044: Domain Models & Services Unit Test Suite
- **Task ID:** TASK-044
- **Task Name:** Domain Models & Services Unit Test Suite
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Complete 100% unit test coverage for pure domain models and services.
- **Description:** Implement unit tests in `tests/unit/domain/` covering immutable dataclasses, `TraceabilityService`, `CoverageService`, `DeduplicationService`, and `DomainValidationService`. Assert domain layer has zero dependency on infrastructure libraries.
- **Dependencies:** TASK-005, TASK-025, TASK-030, TASK-038, TASK-039
- **Expected Input:** Unit testing guidelines in `spec.md §23.1`.
- **Expected Output:** Unit test files in `tests/unit/domain/`.
- **Acceptance Criteria:**
  1. Line coverage for `tcg.domain` reaches >= 85%.
  2. Tests are deterministic and execute in memory without file or network I/O.
- **Definition of Done:** `pytest tests/unit/domain/` passes with required coverage.

---

### TASK-045: Infrastructure Parsers & Extractors Unit Test Suite
- **Task ID:** TASK-045
- **Task Name:** Infrastructure Parsers & Extractors Unit Test Suite
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Verify parser and extractor implementations against synthetic fixture files.
- **Description:** Implement unit tests in `tests/unit/infrastructure/parsers/` and `tests/unit/infrastructure/` testing `DocxBRDParser`, `PdfBRDParser`, `JiraJsonImportParser`, `PdfFlowDiagramParser`, `DiagramExtractor`, `TextExtractor`, and `TableExtractor` against sanitized fixtures.
- **Dependencies:** TASK-013, TASK-014, TASK-015, TASK-019, TASK-020, TASK-021, TASK-022
- **Expected Input:** Parser test requirements in `spec.md §23.1` & `§23.2`.
- **Expected Output:** Unit tests in `tests/unit/infrastructure/`.
- **Acceptance Criteria:**
  1. Evaluates all parsers against synthetic fixture files in `tests/fixtures/`.
  2. Verifies error handling for corrupted or password-protected files.
- **Definition of Done:** `pytest tests/unit/infrastructure/` passes cleanly.

---

### TASK-046: AI Adapters & Response Parser Unit Test Suite
- **Task ID:** TASK-046
- **Task Name:** AI Adapters & Response Parser Unit Test Suite
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Test prompt builder, context assembler, AI response parser, and OpenAI adapter error paths.
- **Description:** Implement unit tests in `tests/unit/infrastructure/test_prompt_builder.py`, `test_context_assembler.py`, `test_response_parser.py`, and `test_openai_adapter.py`. Verify prompt assembly, token budget enforcement, redaction, 5 AI response failure modes, and rate-limit backoff logic.
- **Dependencies:** TASK-028, TASK-029, TASK-031, TASK-032
- **Expected Input:** AI unit test specifications in `plan.md §Phase 4.8` & `§4.9`.
- **Expected Output:** AI unit test files in `tests/unit/infrastructure/`.
- **Acceptance Criteria:**
  1. All 5 AI response parser failure modes tested with pre-recorded fixtures.
  2. Mocked OpenAI adapter verifies HTTP 429 retry backoff logic.
  3. No live AI network calls required for unit test execution.
- **Definition of Done:** All AI unit tests pass in isolation.

---

## 20. Integration Testing

### TASK-047: Document Parsing to Traceability Integration Pipeline Tests
- **Task ID:** TASK-047
- **Task Name:** Document Parsing to Traceability Integration Pipeline Tests
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Test multi-component ingestion, extraction, normalization, and traceability pipeline.
- **Description:** Implement integration tests in `tests/integration/test_brd_to_requirements.py`, `test_jira_to_requirements.py`, and `test_flow_to_paths.py`. Ingest synthetic BRD, JIRA, and Flow PDF fixtures -> run normalizer -> verify `TraceabilityGraph` and `CoverageRecord` generation.
- **Dependencies:** TASK-013, TASK-015, TASK-019, TASK-024, TASK-025
- **Expected Input:** Integration test specs in `plan.md §Phase 3.13`.
- **Expected Output:** Integration tests in `tests/integration/`.
- **Acceptance Criteria:**
  1. Tests complete pipeline from raw file ingestion to normalized requirements.
  2. Verifies graph connectivity between JIRA stories and BRD requirements.
  3. Asserts trace graph is serializable and reloadable from storage.
- **Definition of Done:** Integration tests pass deterministically.

---

### TASK-048: End-to-End Requirement-to-Export Generation Integration Tests
- **Task ID:** TASK-048
- **Task Name:** End-to-End Requirement-to-Export Generation Integration Tests
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Validate pipeline execution from normalized requirements through AI generation, validation, and export.
- **Description:** Implement `tests/integration/test_generation_pipeline.py` and `test_export_pipeline.py`. Execute pipeline: normalized requirements -> mock AI adapter -> draft mapping -> 12 validation gates -> JSON/CSV export. Validate exported JSON against JSON Schema v1.0.
- **Dependencies:** TASK-035, TASK-037, TASK-040, TASK-041
- **Expected Input:** Generation/export integration specs in `plan.md §Phase 4.10` & `§7.7`.
- **Expected Output:** `tests/integration/test_generation_pipeline.py` & `test_export_pipeline.py`.
- **Acceptance Criteria:**
  1. Validates generated cases pass 12 validation gates.
  2. Verifies exported JSON validates against Schema v1.0.
  3. Verifies CSV export contains 19 header columns.
- **Definition of Done:** Pipeline integration tests pass without error.

---

## 21. End-to-End Testing

### TASK-049: CLI Workflow & Smoke End-to-End Test Suite
- **Task ID:** TASK-049
- **Task Name:** CLI Workflow & Smoke End-to-End Test Suite
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Verify all CLI commands and user workflows end-to-end using Click test runner.
- **Description:** Implement `tests/integration/test_cli_smoke.py`. Test complete CLI lifecycle: `tcg run create` -> `tcg ingest` -> `tcg process` -> `tcg generate` (mock AI) -> `tcg validate` -> `tcg review` -> `tcg export` -> `tcg report`.
- **Dependencies:** TASK-007, TASK-035, TASK-037, TASK-040, TASK-043
- **Expected Input:** User journey steps in `prd.md §10`.
- **Expected Output:** `tests/integration/test_cli_smoke.py`.
- **Acceptance Criteria:**
  1. Tests all CLI subcommands in sequence.
  2. Verifies non-zero exit codes on invalid arguments or failed gates.
  3. Confirms end-to-end completion of test generation workflow.
- **Definition of Done:** CLI smoke test suite passes cleanly.

---

## 22. Security

### TASK-050: Role-Based Access Controller (`AccessController`)
- **Task ID:** TASK-050
- **Task Name:** Role-Based Access Controller (`AccessController`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement role-based access control and cross-project authorization checks.
- **Description:** Implement `AccessController` in `src/tcg/infrastructure/security/access_control.py` supporting roles `ANALYST`, `QA_LEAD`, `PRODUCT_OWNER`, `ADMIN` per `spec.md §19.2`. Enforce principal authorization and project/tenant isolation. Emit `ACCESS_DENIED` audit events on unauthorized access.
- **Dependencies:** TASK-005, TASK-012
- **Expected Input:** Security & RBAC specification in `spec.md §19.2`.
- **Expected Output:** `src/tcg/infrastructure/security/access_control.py`.
- **Acceptance Criteria:**
  1. Enforces permissions matrix for analyst, QA lead, product owner, and admin roles.
  2. Blocks cross-project source or test case access.
  3. Emits `ACCESS_DENIED` audit record when check fails.
- **Definition of Done:** Implemented and unit-tested for all role/action combinations.

---

### TASK-051: Fixture Sanitization & Sensitive Data Scan Audit Guard
- **Task ID:** TASK-051
- **Task Name:** Fixture Sanitization & Sensitive Data Scan Audit Guard
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement automated CI guard ensuring no test fixtures or log outputs contain real sensitive data.
- **Description:** Implement `tests/test_fixture_sanitization.py`. Scan all files under `tests/fixtures/` using `SensitiveDataScanner`. Fail test execution if real API keys, card numbers, passwords, or PII patterns are discovered in fixture assets.
- **Dependencies:** TASK-036
- **Expected Input:** Security testing guidelines in `plan.md §Phase 8.6`.
- **Expected Output:** `tests/test_fixture_sanitization.py`.
- **Acceptance Criteria:**
  1. Scans every file in `tests/fixtures/` prior to test runs.
  2. Rejects files containing unmasked secrets or real card numbers.
- **Definition of Done:** Sanitization test passes cleanly on sanitized repository fixtures.

---

## 23. Documentation

### TASK-052: Architecture Decision Records (ADRs)
- **Task ID:** TASK-052
- **Task Name:** Architecture Decision Records (ADRs)
- **Status:** [ ] Not Started
- **Priority:** Medium (P1)
- **Objective:** Record architectural decisions in standardized markdown ADR files under `docs/adr/`.
- **Description:** Create ADRs in `docs/adr/`: `0001-clean-architecture.md`, `0002-pdf-library-selection.md`, `0003-ai-provider-baseline.md`, `0004-file-based-storage-baseline.md`, `0005-prompt-versioning.md`, `0006-sensitive-data-classification.md`, and `0007-test-case-schema-v1.0.md` per `plan.md §Phase 10.2`.
- **Dependencies:** TASK-001
- **Expected Input:** ADR requirements in `plan.md §Phase 10.2`.
- **Expected Output:** ADR files in `docs/adr/`.
- **Acceptance Criteria:**
  1. Formatted according to standard ADR template (Context, Decision, Consequences).
  2. Covers Clean Architecture, PDF parsing, AI provider, storage, prompt versioning, security, and schema choices.
- **Definition of Done:** All 7 ADR documents created and committed.

---

### TASK-053: Technical Limits, Operations & User Documentation
- **Task ID:** TASK-053
- **Task Name:** Technical Limits, Operations & User Documentation
- **Status:** [ ] Not Started
- **Priority:** Medium (P1)
- **Objective:** Author project README, system limitations, and operational runbooks.
- **Description:** Author `README.md` (setup, CLI usage, configuration), `docs/limitations.md` (file sizes, English scope, OCR constraints, out-of-scope features), and `docs/operations.md` (API key rotation, audit log management, dependency updates, security response) per `plan.md §Phase 10.1, 10.3, 10.9`.
- **Dependencies:** TASK-007, TASK-043
- **Expected Input:** Documentation specifications in `plan.md §Phase 10`.
- **Expected Output:** `README.md`, `docs/limitations.md`, `docs/operations.md`.
- **Acceptance Criteria:**
  1. `README.md` details environment setup, CLI quick-start, and configuration.
  2. `docs/limitations.md` documents technical boundaries per AC-025.
  3. `docs/operations.md` outlines key rotation, audit management, and incident response.
- **Definition of Done:** Documentation complete and reviewed for clarity.

---

## 24. CI/CD

### TASK-054: GitHub Actions CI/CD Pipeline Automation (`ci.yml`)
- **Task ID:** TASK-054
- **Task Name:** GitHub Actions CI/CD Pipeline Automation (`ci.yml`)
- **Status:** [ ] Not Started
- **Priority:** High (P0)
- **Objective:** Implement GitHub Actions workflow for automated testing, type-checking, secret scanning, security auditing, and release packaging.
- **Description:** Implement `.github/workflows/ci.yml`. Define workflow jobs running on push and pull request: Python 3.11 setup, `ruff check`, `mypy src/tcg/`, `pytest` with coverage enforcement (`--cov-fail-under=70`), `pip-audit` for CVE scanning, and release tagging job.
- **Dependencies:** TASK-002, TASK-044, TASK-048, TASK-049
- **Expected Input:** CI/CD specifications in `plan.md §Phase 1.10` & `§Phase 10.4`.
- **Expected Output:** `.github/workflows/ci.yml`.
- **Acceptance Criteria:**
  1. Runs linting (`ruff`), type-checking (`mypy`), and unit/integration tests (`pytest`) on Python 3.11.
  2. Enforces line coverage threshold >= 70%.
  3. Runs `pip-audit` to block builds with known vulnerabilities.
  4. Automation passes cleanly on repository pushes.
- **Definition of Done:** `.github/workflows/ci.yml` committed and verified via GitHub Actions execution.
