# AI-Powered Test Case Generator Samples

## Purpose

This folder contains a small, fictional evidence set for developing, testing, validating, and demonstrating the AI-Powered Test Case Generator. The three files describe one consistent Demo Bank fund-transfer journey:

- [BRD workbook](brd/sample_brd.xlsx) - structured business requirements, functional requirements, rules, validations, and symbolic test data.
- [JIRA story](jira/sample_jira_user_story.md) - story `PAY-101` with business context and Given/When/Then acceptance criteria.
- [Flow diagram PDF](flow_diagrams/sample_payment_flow.pdf) - a vector, text-extractable end-to-end flow with decisions, alternate paths, and an exception path.

Every customer, account, beneficiary, and transaction value is a synthetic token. No real customer information, account number, transaction identifier, credential, or confidential banking data is included.

## Source Relationship

The BRD workbook is the broadest source. JIRA story `PAY-101` restates the same behavior as an implementation-sized story and uses acceptance criteria as expected-behavior evidence. The PDF represents the executable workflow and supplies main, alternate, and exception paths. The same terminology is used across all three files: `source account`, `beneficiary`, `transfer amount`, `available balance`, `daily transfer limit`, `duplicate transaction`, `payment processor`, `transaction reference`, and `confirmation`.

The current technical specification lists DOCX and PDF as baseline BRD formats and structured JSON as the baseline JIRA format. This requested workbook is an Excel demonstration input. An implementation that follows the current baseline must either add an approved Excel source adapter or convert this workbook through a controlled adapter before ingestion; it must not silently claim that `.xlsx` is supported if it is not configured.

## Expected Processing Sequence

1. Register the sample set under one authorized project and generation run.
2. Capture source identifiers, versions or checksums, classifications, and processing metadata.
3. Preflight each source and report unsupported formats, missing fields, duplicates, unreadable content, or other failures.
4. Parse the workbook, Markdown story, and PDF without changing source files.
5. Extract requirements, rule rows, validation rows, acceptance criteria, text labels, nodes, connectors, decisions, and paths with source locations and confidence.
6. Normalize identifiers and terminology while preserving original representations.
7. Correlate BRD requirements, JIRA criteria, and flow paths; surface unresolved links or conflicts for human review.
8. Plan applicable positive, negative, boundary, validation, exception, integration, and end-to-end scenario classes.
9. Assemble only the required evidence, redact sensitive patterns, and generate structured draft cases with citations.
10. Run schema, identity, security, traceability, evidence, coverage, consistency, duplicate, audit, and review gates.
11. Present drafts for human review. Validation success must not be treated as approval.
12. Export only according to the configured review and approval policy, preserving schema version, source references, validation status, and review status.

## Traceability Example

```text
BRD-PAY-001 -> PAY-101 -> FLOW-PAY-MAIN / FLOW-PAY-SUCCESS
BRD-PAY-002 -> PAY-101 -> FLOW-PAY-ALT-002
BRD-PAY-003 -> PAY-101 -> FLOW-PAY-ALT-004
BRD-PAY-004 -> PAY-101 -> FLOW-PAY-ALT-003
BRD-PAY-005 -> PAY-101 -> FLOW-PAY-ALT-003
BRD-PAY-006 -> PAY-101 -> FLOW-PAY-ALT-005
BRD-PAY-007 -> PAY-101 -> FLOW-PAY-ALT-006
BRD-PAY-008 -> PAY-101 -> FLOW-PAY-ALT-001
BRD-PAY-009 -> PAY-101 -> FLOW-PAY-EXC-001
BRD-PAY-010 -> PAY-101 -> FLOW-PAY-SUCCESS
BRD-PAY-011 -> PAY-101 -> FLOW-PAY-MAIN
```

The acceptance criteria in the JIRA file repeat these mappings inline. `BRD-PAY-012` is not used; the workbook intentionally contains 11 requirements (`BRD-PAY-001` through `BRD-PAY-011`) so every requirement can be traced to the story and flow.

## Expected Scenario Coverage

| Scenario class | Sample evidence | Example cases |
|---|---|---|
| Positive | Valid account, beneficiary, amount, balance, limit, and processor success | Complete transfer; confirmation with transaction reference |
| Negative | Invalid beneficiary, invalid account details, insufficient balance, duplicate request | Rejection before payment processing |
| Boundary | USD 1.00, USD 25,000.00, USD 25,000.01, and USD 50,000.00 daily total | Inclusive amount limits; just-outside limit |
| Validation | Mandatory fields, account format, two-decimal amount, active beneficiary | Field and business-rule validation outcomes |
| Exception | Payment processor failure or unavailability | Failed outcome without a success confirmation |
| Integration | Authentication, account/beneficiary validation, balance, limit, history, and payment processor dependencies | Service handoffs and processor response handling |
| End-to-end | `FLOW-PAY-MAIN`, alternate paths, and success/failure termination states | Start-to-finish transfer journeys |

## Workbook Contents

- `Business_Requirements` - 11 requirements with IDs, descriptions, functional behavior, rules, validations, expected behavior, priority, and dependencies.
- `Functional_Requirements` - implementation-oriented behavior statements linked to BRD requirements.
- `Business_Rules` - authoritative sample rules and boundary values used by the generator.
- `Validation_Rules` - field-level, account, balance, limit, duplicate, and authorization checks.
- `Test_Data` - symbolic positive, negative, boundary, and exception data values.

## Using the Samples in Tests

- **Parser unit tests:** assert workbook sheet names and requirement IDs, Markdown field and criterion extraction, and PDF text/layout extraction.
- **Normalization tests:** assert stable BRD IDs, JIRA story and criterion relationships, normalized terminology, and preserved original text.
- **Traceability tests:** assert each mapped requirement has at least one source reference and that flow path IDs resolve to PDF page locations.
- **Scenario tests:** assert applicability for all seven scenario classes, especially explicit amount and daily-limit boundaries.
- **Generation tests:** use a deterministic mock AI provider and require citations to BRD IDs, `PAY-101` criteria, or flow path IDs.
- **Validation tests:** inject malformed citations, placeholder expected results, duplicate drafts, and symbolic sensitive-data patterns in isolated fixtures.
- **Export tests:** verify schema version, stable IDs, review state, validation status, and traceability fields in JSON and CSV outputs.
- **CLI/end-to-end tests:** run the configured intake, processing, generation, validation, review, export, and report commands using a temporary storage directory and no live JIRA or AI service.

## Data and Review Boundaries

The samples define fictional behavior only. They do not authorize production behavior, establish a real bank policy, or replace stakeholder approval. The review questions in the JIRA story are unresolved by design. A generator must label assumptions and questions, preserve conflicts, and request human clarification rather than filling in missing business rules.
