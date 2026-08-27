# PAY-101 - Fund Transfer from an Eligible Source Account

- **JIRA Story ID:** PAY-101
- **JIRA Reference:** https://jira.example.com/browse/PAY-101
- **Summary:** Allow an authenticated customer to submit a validated fund transfer
- **Priority:** High
- **Labels:** `payments`, `fund-transfer`, `customer-journey`, `sample-data`
- **Dependencies:** Authentication service; account and beneficiary validation service; balance service; daily-limit service; payment processor; transaction history service

## Description

The fictional Demo Bank payment experience must allow an authenticated customer to transfer funds from an eligible source account to a registered beneficiary. The system validates account details, beneficiary status, mandatory fields, amount rules, available balance, the daily transfer limit, and recent duplicate activity before submitting a transfer to the payment processor.

The story is intentionally aligned with the workbook in `../brd/sample_brd.xlsx` and the flow diagram in `../flow_diagrams/sample_payment_flow.pdf`. All account, customer, and transaction values in these samples are symbolic test tokens and do not represent real banking data.

## Business Objective

Provide a clear, controlled, and traceable fund-transfer journey that accepts valid transfers, rejects invalid or unsafe requests before processing, and gives the customer an unambiguous success or failure outcome.

## User Story

**As an authenticated Demo Bank customer, I want to transfer funds to a valid beneficiary from an eligible source account, so that I can complete a secure payment and receive confirmation when processing succeeds.**

## Business Rules

| Rule ID | Rule | Related BRD requirements |
|---|---|---|
| BR-RULE-001 | Transfer amount must be from USD 1.00 through USD 25,000.00 inclusive and use no more than two decimal places. | BRD-PAY-004 |
| BR-RULE-002 | Source account, beneficiary account, and transfer amount are mandatory. | BRD-PAY-005 |
| BR-RULE-003 | The source account must belong to the authenticated customer and be eligible for transfers. | BRD-PAY-011 |
| BR-RULE-004 | Account identifiers must have an accepted format and pass account-status validation. | BRD-PAY-008 |
| BR-RULE-005 | A beneficiary must be registered and active before the transfer can proceed. | BRD-PAY-002 |
| BR-RULE-006 | Available balance must be at least the requested transfer amount. | BRD-PAY-003 |
| BR-RULE-007 | The cumulative transfer amount for the business day must remain at or below USD 50,000.00. | BRD-PAY-006 |
| BR-RULE-008 | A transfer with the same source, beneficiary, and amount within five minutes is treated as a duplicate. | BRD-PAY-007 |
| BR-RULE-009 | A payment processor failure produces a failed outcome and must not be reported as successful. | BRD-PAY-009 |
| BR-RULE-010 | A successful processor response creates a transaction reference and customer confirmation. | BRD-PAY-001, BRD-PAY-010 |

## Acceptance Criteria

### AC-PAY-101-01 - Submit a valid transfer

**Traceability:** BRD-PAY-001, BRD-PAY-004, BRD-PAY-005, BRD-PAY-010; `FLOW-PAY-MAIN`

```text
Given the customer is authenticated
And the source account belongs to the customer and is eligible for transfers
And the beneficiary account is registered and active
And the source account has available balance of at least the transfer amount
And the transfer amount is between USD 1.00 and USD 25,000.00 inclusive
And the transfer does not exceed the daily transfer limit
And the transfer is not a duplicate within the five-minute duplicate window
When the customer submits a valid fund transfer
Then the system validates the transaction
And submits it to the payment processor
And generates a transaction reference when the processor reports success
And displays a confirmation containing the transaction reference
```

### AC-PAY-101-02 - Reject an invalid beneficiary

**Traceability:** BRD-PAY-002; `FLOW-PAY-ALT-002`

```text
Given the customer is authenticated
And the beneficiary is not registered or is inactive
When the customer submits the fund transfer
Then the system rejects the transfer before payment processing
And displays an invalid beneficiary outcome
And does not generate a success confirmation
```

### AC-PAY-101-03 - Reject invalid account details

**Traceability:** BRD-PAY-008, BRD-PAY-011; `FLOW-PAY-ALT-001`

```text
Given the customer is authenticated
And the source account or beneficiary account details fail format or status validation
When the customer submits the fund transfer
Then the system rejects the transfer before payment processing
And displays an invalid account details outcome
And does not debit the source account
```

### AC-PAY-101-04 - Validate mandatory fields and transaction amount boundaries

**Traceability:** BRD-PAY-004, BRD-PAY-005; `FLOW-PAY-ALT-003`

```text
Given the customer is authenticated
When the customer submits a transfer with a missing source account, beneficiary account, or transaction amount
Or the customer submits an amount below USD 1.00 or above USD 25,000.00
Or the customer submits an amount with more than two decimal places
Then the system rejects the request before payment processing
And displays a validation outcome
And does not generate a transaction reference
```

### AC-PAY-101-05 - Reject an insufficient-balance transfer

**Traceability:** BRD-PAY-003; `FLOW-PAY-ALT-004`

```text
Given the customer is authenticated
And all account, beneficiary, field, and amount validations pass
And the available source-account balance is less than the transfer amount
When the customer submits the fund transfer
Then the system rejects the transfer before payment processing
And displays an insufficient balance outcome
And does not debit the source account
```

### AC-PAY-101-06 - Enforce the daily transaction limit

**Traceability:** BRD-PAY-006; `FLOW-PAY-ALT-005`

```text
Given the customer is authenticated
And the transfer is otherwise valid
And adding the requested amount would make the business-day cumulative transfer total greater than USD 50,000.00
When the customer submits the fund transfer
Then the system rejects the transfer before payment processing
And displays a transaction limit exceeded outcome
And does not generate a transaction reference
```

### AC-PAY-101-07 - Reject a duplicate transaction

**Traceability:** BRD-PAY-007; `FLOW-PAY-ALT-006`

```text
Given the customer has submitted a transfer with the same source account, beneficiary account, and amount within the last five minutes
When the customer submits the same transfer again
Then the system identifies the request as a duplicate
And rejects it before payment processing
And does not create a second successful transfer
```

### AC-PAY-101-08 - Handle payment processing failure

**Traceability:** BRD-PAY-009; `FLOW-PAY-EXC-001`

```text
Given the transfer passes local validation and is submitted to the payment processor
When the payment processor reports a failure or is unavailable
Then the system records a failed transfer outcome
And displays a payment processing error outcome
And does not display the transfer as successful
```

### AC-PAY-101-09 - Confirm a successful transfer

**Traceability:** BRD-PAY-010; `FLOW-PAY-SUCCESS`

```text
Given the payment processor reports a successful transfer
When the system receives the successful response
Then the system generates a unique transaction reference
And displays the confirmation outcome
And includes the transfer amount, beneficiary reference, and transaction reference
```

## Review Questions

- Confirm the production currency and whether the sample USD values should be replaced by a project currency before evaluation.
- Confirm whether the daily limit includes pending transfers as well as completed transfers.
- Confirm the authoritative source for the five-minute duplicate window if the BRD and JIRA story are changed independently.

These questions are intentionally separated from the acceptance criteria so an implementation must not treat them as confirmed business behavior.
