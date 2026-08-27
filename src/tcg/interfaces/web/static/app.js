const scenarioDescriptions = {
  POSITIVE: 'Valid and successful behavior',
  NEGATIVE: 'Invalid input or rejected behavior',
  BOUNDARY: 'Explicit limits and edge values',
  VALIDATION: 'Required fields and business rules',
  EXCEPTION: 'Failure and unavailable dependencies',
  INTEGRATION: 'Named service and system handoffs',
  END_TO_END: 'Complete resolved workflow paths',
};

const state = {
  run: null,
  runs: [],
  counts: { sources: 0, requirements: 0, cases: 0, coverage: 0 },
  sources: [],
  requirements: [],
  criteria: [],
  flow_paths: [],
  cases: [],
  coverage: [],
  traceability: [],
  reports: {},
  scenario_types: Object.keys(scenarioDescriptions),
  generation: null,
};
let selectedCaseId = null;
let activeReportType = 'summary';

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[character]));
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const contentType = response.headers.get('content-type') || '';
  const body = contentType.includes('application/json') ? await response.json() : await response.blob();
  if (!response.ok) throw new Error(body.error || 'The request could not be completed');
  return body;
}

function jsonOptions(method, body) {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}

function showFlash(message, error = false) {
  const flash = $('#flash');
  flash.textContent = message;
  flash.classList.toggle('error', error);
  flash.classList.add('visible');
  window.clearTimeout(showFlash.timer);
  showFlash.timer = window.setTimeout(() => flash.classList.remove('visible'), 5000);
}

function activeRunId() {
  return state.run?.run_id || $('#run-select').value || '';
}

function applyState(payload) {
  Object.assign(state, payload);
  const select = $('#run-select');
  select.innerHTML = state.runs.length
    ? state.runs.map((run) => `<option value="${escapeHtml(run.run_id)}">${escapeHtml(run.project_name)} · ${escapeHtml(run.run_id)}</option>`).join('')
    : '<option value="">No active run</option>';
  if (state.run) select.value = state.run.run_id;
  renderAll();
}

function renderAll() {
  const counts = state.counts || {};
  $('#metric-sources').textContent = counts.sources || 0;
  $('#metric-requirements').textContent = counts.requirements || 0;
  $('#metric-cases').textContent = counts.cases || 0;
  $('#metric-cases-caption').textContent = `${counts.awaiting_review_cases || 0} awaiting review · ${counts.approved_cases || 0} approved${counts.rejected_cases ? ` · ${counts.rejected_cases} rejected` : ''}`;
  $('#metric-coverage').innerHTML = `${counts.coverage || 0}<span class="metric-suffix">%</span>`;
  $('#run-status').textContent = state.run ? `${state.run.status} · ${state.run.project_name}` : 'No run loaded';
  renderPipeline();
  renderSignals();
  renderSources();
  renderDocuments();
  renderScenarios();
  renderCases();
  renderTraceability();
  renderCoverage();
  renderReports();
}

function renderPipeline() {
  const stages = [
    ['01', 'Sources', state.counts.sources > 0],
    ['02', 'Validated', state.requirements.length > 0],
    ['03', 'Planned', state.scenario_types.length > 0 && state.requirements.length > 0],
    ['04', 'Generated', state.cases.length > 0],
    ['05', 'Reviewed', state.cases.some((item) => item.review_status === 'APPROVED')],
  ];
  $('#pipeline-steps').innerHTML = stages.map(([number, label, done]) => `<div class="pipeline-step ${done ? 'done' : ''} ${!done && state.run ? 'current' : ''}"><div class="step-marker">${done ? '&#10003;' : number}</div><strong>${label}</strong><small>${done ? 'Complete' : 'Pending'}</small></div>`).join('');
  const status = state.run?.status || 'NOT STARTED';
  $('#readiness-badge').textContent = status.replaceAll('_', ' ');
  $('#readiness-caption').textContent = state.run ? `${state.counts.sources} sources registered · ${state.counts.approved_cases || 0} approved · ${state.counts.awaiting_review_cases || 0} awaiting review.` : 'Load the sample set to begin.';
}

function renderSignals() {
  const signals = state.signals || [];
  $('#warning-count').textContent = signals.length;
  $('#signal-list').innerHTML = signals.length
    ? signals.slice(-5).map((signal) => `<div class="signal-item">${escapeHtml(signal)}</div>`).join('')
    : '<div class="signal-item empty">No unresolved processing signals in the active run.</div>';
}

function renderSources() {
  $('#source-count-badge').textContent = `${state.sources.length} SOURCE${state.sources.length === 1 ? '' : 'S'}`;
  $('#source-table').innerHTML = state.sources.length ? state.sources.map((source) => `<tr><td>${escapeHtml(source.filename)}<small class="table-secondary">${escapeHtml(source.source_id)}</small></td><td>${escapeHtml(source.source_type.replaceAll('_', ' '))}</td><td><span class="badge ${source.status === 'COMPLETED' ? 'badge-green' : 'badge-gold'}">${escapeHtml(source.status.replaceAll('_', ' '))}</span></td><td>${source.item_count}</td><td>${source.warning_count ? 'Review warnings' : 'High'}</td></tr>`).join('') : '<tr><td colspan="5" class="empty-state">No evidence registered yet.</td></tr>';
}

function renderDocuments() {
  const requirementItems = state.requirements || [];
  const criteriaItems = state.criteria || [];
  const pathItems = state.flow_paths || [];
  $('#extraction-count').textContent = `${requirementItems.length + criteriaItems.length + pathItems.length} ITEMS`;
  $('#requirement-preview').innerHTML = requirementItems.length
    ? requirementItems.slice(0, 8).map((item) => `<div class="preview-item"><strong>${escapeHtml(item.requirement_id)}</strong>${escapeHtml(item.description)}<small>${escapeHtml(item.location?.label || 'BRD source location')}</small></div>`).join('')
    : '<div class="preview-item">No normalized requirements yet.</div>';
  $('#criteria-preview').innerHTML = criteriaItems.length
    ? criteriaItems.slice(0, 8).map((item) => `<div class="preview-item"><strong>${escapeHtml(item.criterion_id)}</strong>${escapeHtml(item.text.slice(0, 135))}${item.text.length > 135 ? '...' : ''}<small>${escapeHtml(item.requirement_ids.join(', ') || 'No BRD link')}</small></div>`).join('')
    : '<div class="preview-item">No acceptance criteria yet.</div>';
  $('#flow-preview').innerHTML = pathItems.length
    ? pathItems.map((item) => `<div class="preview-item"><strong>${escapeHtml(item.path_id)}</strong>${escapeHtml(item.name)}<small>${escapeHtml(item.path_type)} · ${item.complete ? 'Complete path' : 'Needs review'}</small></div>`).join('')
    : '<div class="preview-item">No flow paths yet.</div>';
}

function renderScenarios() {
  const selected = state.scenario_types || Object.keys(scenarioDescriptions);
  $('#scenario-options').innerHTML = Object.entries(scenarioDescriptions).map(([type, description]) => `<label class="scenario-option"><input type="checkbox" value="${type}" ${selected.includes(type) ? 'checked' : ''}><span><strong>${type.replaceAll('_', ' ')}</strong><small>${description}</small></span></label>`).join('');
  const plans = state.scenario_plans || [];
  $('#plan-count').textContent = `${plans.length || 0} PLANS`;
  $('#selected-type-caption').textContent = `${selected.length} classes selected`;
  const counts = selected.map((type) => [type, state.requirements.filter((requirement) => {
    const hasSignal = type === 'POSITIVE' || type === 'END_TO_END' || requirement.validation || requirement.dependencies?.length;
    return Boolean(hasSignal);
  }).length]);
  $('#plan-preview').innerHTML = counts.length ? counts.map(([type, count]) => `<div class="plan-row"><span>${type.replaceAll('_', ' ')}</span><strong>${count} requirement${count === 1 ? '' : 's'} considered</strong></div>`).join('') : '<div class="empty-state">Process documents to preview scenario applicability.</div>';
}

function renderCases() {
  const search = ($('#case-search')?.value || '').toLowerCase();
  const type = $('#case-type-filter')?.value || '';
  const review = $('#case-status-filter')?.value || '';
  const typeFilter = $('#case-type-filter');
  if (typeFilter && typeFilter.options.length === 1) {
    typeFilter.innerHTML += Object.keys(scenarioDescriptions).map((item) => `<option value="${item}">${item.replaceAll('_', ' ')}</option>`).join('');
  }
  const cases = state.cases.filter((item) => {
    const haystack = `${item.test_case_id} ${item.requirement_id} ${item.scenario}`.toLowerCase();
    return (!search || haystack.includes(search)) && (!type || item.test_type === type) && (!review || item.review_status === review);
  });
  $('#case-count').textContent = `${cases.length} case${cases.length === 1 ? '' : 's'}`;
  $('#case-empty').style.display = cases.length ? 'none' : 'block';
  if (!cases.length) {
    const failures = (state.signals || []).filter((signal) => signal.startsWith('Generation failed for '));
    $('#case-empty').textContent = failures.length
      ? `Generation did not create a case. ${failures.length} provider failure${failures.length === 1 ? '' : 's'} recorded; retry generation after checking the backend provider.`
        : state.cases.length
          ? 'No cases match the current search or filters.'
      : 'No generated cases yet. Run generation to create recommendations.';
  }
  $('#case-table').innerHTML = cases.map((item) => `<tr><td><span class="case-id">${escapeHtml(item.test_case_number || 'Unnumbered')}</span><span class="case-title">${escapeHtml(item.scenario)}</span></td><td>${escapeHtml(item.requirement_id)}</td><td><span class="type-pill">${escapeHtml(item.test_type.replaceAll('_', ' '))}</span></td><td class="${item.priority === 'HIGH' || item.priority === 'CRITICAL' ? 'priority-high' : 'priority-medium'}">${escapeHtml(item.priority)}</td><td class="${validationClass(item.validation_status, item.review_status)}">${validationMarkup(item)}</td><td><span class="badge ${item.review_status === 'APPROVED' ? 'badge-green' : item.review_status === 'NEEDS_REVIEW' ? 'badge-gold' : 'badge-muted'}">${escapeHtml(item.review_status.replaceAll('_', ' '))}</span></td><td><button class="inline-action" data-case-id="${escapeHtml(item.test_case_id)}">View / edit</button></td></tr>`).join('');
}

function validationLabel(status) {
  return {
    PASSED: 'PASSED',
    WARNING: 'REVIEW REQUIRED',
    FAILED: 'FAILED',
    BLOCKED: 'BLOCKED',
  }[status] || status.replaceAll('_', ' ');
}

function validationClass(status, reviewStatus = '') {
  if (reviewStatus === 'APPROVED') return 'validation-approved-cell';
  return {
    PASSED: 'validation-passed',
    WARNING: 'validation-review',
    FAILED: 'validation-blocked',
    BLOCKED: 'validation-blocked',
  }[status] || 'validation-review';
}

function validationMarkup(item) {
  if (item.review_status === 'APPROVED') {
    return `<span class="validation-approved">APPROVED</span><small class="validation-note">Quality: ${escapeHtml(validationLabel(item.validation_status))}</small>`;
  }
  return escapeHtml(validationLabel(item.validation_status));
}

function renderTraceability() {
  $('#trace-count').textContent = `${state.traceability.length} REQUIREMENTS`;
  $('#trace-list').innerHTML = state.traceability.length ? state.traceability.map((row) => `<div class="trace-row"><div class="trace-cell"><label>BRD requirement</label><strong class="trace-token">${escapeHtml(row.requirement_id)}</strong><span>${escapeHtml(row.description)}</span></div><div class="trace-cell"><label>JIRA story</label><strong class="trace-token">${escapeHtml(row.jira_story_id || 'Not linked')}</strong></div><div class="trace-cell"><label>Acceptance criteria</label>${row.criteria.length ? row.criteria.map((item) => `<span class="trace-token">${escapeHtml(item.id)}</span>`).join('') : '<span>Unresolved</span>'}</div><div class="trace-cell"><label>Flow path</label>${row.flow_paths.length ? row.flow_paths.map((item) => `<span class="trace-token">${escapeHtml(item.id)}</span>`).join('') : '<span>Unresolved</span>'}</div><div class="trace-cell"><label>Test cases</label>${row.test_cases.length ? `<span>${row.test_cases.length} linked · ${escapeHtml(row.test_cases[0].status.replaceAll('_', ' '))}</span>` : '<span>Uncovered</span>'}</div></div>`).join('') : '<div class="empty-state">Process the evidence set to build the traceability graph.</div>';
}

function renderCoverage() {
  const coverage = state.coverage || [];
  const average = coverage.length ? Math.round(coverage.reduce((total, item) => total + Number(item.coverage_percentage), 0) / coverage.length) : 0;
  $('#coverage-average').textContent = `${average}% average`;
  $('#gap-count').textContent = `${coverage.filter((item) => item.orphan).length} GAPS`;
  const typeCounts = Object.keys(scenarioDescriptions).map((type) => [type, coverage.reduce((total, item) => total + ((item.covered || []).includes(type) ? 1 : 0), 0)]);
  $('#coverage-bars').innerHTML = typeCounts.map(([type, count]) => `<div class="coverage-bar-row"><span>${type.replaceAll('_', ' ')}</span><div class="coverage-track"><div class="coverage-fill" style="width:${coverage.length ? Math.round(count / coverage.length * 100) : 0}%"></div></div><strong>${coverage.length ? Math.round(count / coverage.length * 100) : 0}%</strong></div>`).join('');
  const gaps = coverage.filter((item) => item.orphan);
  $('#gap-list').innerHTML = gaps.length ? gaps.map((item) => `<div class="gap-item"><div><strong>${escapeHtml(item.entity_id)}</strong>${escapeHtml(item.description)}</div></div>`).join('') : '<div class="signal-item empty">Every normalized requirement has at least one linked recommendation.</div>';
  $('#coverage-table').innerHTML = coverage.map((item) => `<tr><td>${escapeHtml(item.entity_id)}<small class="table-secondary">${escapeHtml(item.description)}</small></td><td>${item.applicable.length}</td><td>${item.covered.length}</td><td>${item.unresolved.length}</td><td><strong>${item.coverage_percentage}%</strong></td><td><span class="badge ${item.orphan ? 'badge-coral' : 'badge-green'}">${item.orphan ? 'UNCOVERED' : 'LINKED'}</span></td></tr>`).join('');
}

function renderReports() {
  const report = state.reports?.[activeReportType] || state.reports?.summary;
  if (!report) {
    $('#report-title').textContent = 'Select a report';
    $('#report-output').innerHTML = '<div class="report-empty">Choose a report view after processing a generation run.</div>';
    return;
  }
  $('#report-title').textContent = reportTitle(activeReportType);
  $('#report-output').innerHTML = renderReportPreview(activeReportType, report);
}

function reportTitle(type) {
  return {
    summary: 'Generation summary',
    traceability: 'Traceability matrix',
    coverage: 'Coverage report',
    quality: 'Quality gates',
    review: 'Review status',
    change_impact: 'Change impact',
  }[type] || 'Report preview';
}

function reportMetric(label, value, detail, tone = '') {
  return `<div class="report-kpi ${tone}"><span class="report-kpi-label">${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(detail)}</small></div>`;
}

function reportStatus(label, tone) {
  return `<span class="report-status report-status-${tone}">${escapeHtml(label)}</span>`;
}

function reportTypes(types) {
  return types?.length
    ? types.map((type) => `<span class="report-type-pill">${escapeHtml(type.replaceAll('_', ' '))}</span>`).join('')
    : '<span class="report-muted">None recorded</span>';
}

function renderReportPreview(type, report) {
  if (type === 'coverage' && Array.isArray(report)) return renderCoverageReport(report);
  if (type === 'traceability' && Array.isArray(report)) return renderTraceabilityReport(report);
  if (type === 'summary') return renderSummaryReport(report);
  if (type === 'quality') return renderQualityReport(report);
  if (type === 'review') return renderReviewReport(report);
  if (type === 'change_impact') return renderChangeImpactReport(report);
  return '<div class="report-empty">This report has no readable content.</div>';
}

function renderSummaryReport(report) {
  const warnings = Number(report.warnings || 0);
  const priorities = report.priority_distribution || {};
  return `<div class="report-preview-body"><div class="report-kpi-grid">${reportMetric('Sources', report.source_count || 0, 'Evidence items registered')}${reportMetric('Requirements', report.requirements || 0, 'Normalized behavior units', 'tone-blue')}${reportMetric('Test cases', report.test_cases || 0, 'Recommendations in the run', 'tone-gold')}${reportMetric('Coverage', `${report.coverage || 0}%`, 'Average applicable coverage', 'tone-green')}</div><div class="report-section"><div class="report-section-heading"><div><span class="eyebrow">RUN OVERVIEW</span><h3>${escapeHtml(report.project_name || 'Generation run')}</h3></div>${reportStatus(warnings ? 'Review signals present' : 'Ready for review', warnings ? 'attention' : 'good')}</div><div class="report-point-grid"><div class="report-point"><strong>Evidence assembled</strong><span>${escapeHtml(`${report.source_count || 0} sources produced ${report.requirements || 0} normalized requirements and ${report.flow_paths || 0} flow paths.`)}</span></div><div class="report-point"><strong>Review posture</strong><span>${escapeHtml(`${report.test_cases || 0} recommendations are available for human review. Validation does not imply approval.`)}</span></div><div class="report-point"><strong>Action required</strong><span>${warnings ? escapeHtml(`${warnings} processing or review signal${warnings === 1 ? '' : 's'} should be inspected before export.`) : 'No processing warnings are recorded for this run.'}</span></div></div></div>${renderPriorityPie(priorities)}<div class="report-footnote">Run ID: <strong>${escapeHtml(report.run_id || 'Not available')}</strong></div></div>`;
}

function renderPriorityPie(distribution) {
  const colors = { CRITICAL: '#b94d4d', HIGH: '#2867b2', MEDIUM: '#b07b24', LOW: '#2e8063', UNKNOWN: '#93a1ad' };
  const labels = { CRITICAL: 'Critical', HIGH: 'High', MEDIUM: 'Medium', LOW: 'Low', UNKNOWN: 'Unknown' };
  const entries = Object.entries(distribution).filter(([, value]) => Number(value) > 0);
  const total = entries.reduce((sum, [, value]) => sum + Number(value), 0);
  if (!total) return '<div class="report-section report-empty">No priority data is available for this run.</div>';
  let cursor = 0;
  const segments = entries.map(([priority, value]) => {
    const start = cursor;
    cursor += Number(value) / total * 100;
    return `${colors[priority] || colors.UNKNOWN} ${start}% ${cursor}%`;
  }).join(', ');
  const legend = entries.map(([priority, value]) => `<div class="pie-legend-row"><span class="pie-swatch" style="background:${colors[priority] || colors.UNKNOWN}"></span><span>${escapeHtml(labels[priority] || priority)}</span><strong>${escapeHtml(value)}</strong><small>${Math.round(Number(value) / total * 100)}%</small></div>`).join('');
  return `<div class="report-section"><div class="report-section-heading"><div><span class="eyebrow">PRIORITY MIX</span><h3>Reviewer-assigned priority</h3></div><span class="report-status report-status-good">${escapeHtml(`${total} cases`)}</span></div><div class="priority-chart"><div class="priority-pie" role="img" aria-label="Priority distribution for ${total} test cases" style="background:conic-gradient(${segments})"><div class="priority-pie-center"><strong>${total}</strong><span>cases</span></div></div><div class="pie-legend">${legend}</div></div><p class="report-lead">Priority reflects the latest reviewer assignment. Changes made in Test Cases are reflected here after the run state refreshes.</p></div>`;
}

function renderCoverageReport(report) {
  const average = report.length ? Math.round(report.reduce((total, item) => total + Number(item.coverage_percentage || 0), 0) / report.length) : 0;
  const fullyCovered = report.filter((item) => Number(item.coverage_percentage) >= 100).length;
  const gaps = report.filter((item) => item.orphan).length;
  const unresolved = report.filter((item) => (item.unresolved || []).length).length;
  const rows = report.map((item) => `<tr><td><strong>${escapeHtml(item.entity_id)}</strong><small class="table-secondary">${escapeHtml(item.description)}</small></td><td><div class="report-inline-bar"><span style="width:${Math.min(Number(item.coverage_percentage || 0), 100)}%"></span></div><strong>${escapeHtml(`${item.coverage_percentage || 0}%`)}</strong></td><td>${item.covered?.length || 0} / ${item.applicable?.length || 0}</td><td>${item.unresolved?.length || 0}</td><td>${item.orphan ? reportStatus('Action required', 'attention') : reportStatus('Covered', 'good')}</td></tr>`).join('');
  return `<div class="report-preview-body"><div class="report-kpi-grid">${reportMetric('Average coverage', `${average}%`, 'Across normalized requirements', 'tone-green')}${reportMetric('Fully covered', `${fullyCovered}/${report.length}`, 'Requirements at 100%', 'tone-blue')}${reportMetric('Uncovered', gaps, 'Requirements without cases', gaps ? 'tone-coral' : 'tone-green')}${reportMetric('Unresolved', unresolved, 'Requirements with open classes', unresolved ? 'tone-gold' : 'tone-green')}</div><div class="report-section"><div class="report-section-heading"><div><span class="eyebrow">COVERAGE POSTURE</span><h3>Requirement-level readiness</h3></div>${reportStatus(gaps || unresolved ? 'Follow-up required' : 'Complete', gaps || unresolved ? 'attention' : 'good')}</div><p class="report-lead">Coverage is calculated from applicable scenario classes only. Excluded classes retain their evidence-based rationale and are not counted as missed coverage.</p><div class="table-wrap report-table-wrap"><table class="report-table"><thead><tr><th>Requirement</th><th>Coverage</th><th>Scenario classes</th><th>Open</th><th>Readiness</th></tr></thead><tbody>${rows || '<tr><td colspan="5" class="report-empty">No coverage records available.</td></tr>'}</tbody></table></div></div></div>`;
}

function renderTraceabilityReport(report) {
  const linked = report.filter((item) => item.test_cases?.length).length;
  const rows = report.map((item) => `<tr><td><strong class="trace-token">${escapeHtml(item.requirement_id)}</strong><small class="table-secondary">${escapeHtml(item.description)}</small></td><td>${escapeHtml(item.jira_story_id || 'Not linked')}</td><td>${item.criteria?.length || 0}</td><td>${item.flow_paths?.length || 0}</td><td>${item.test_cases?.length || 0}</td></tr>`).join('');
  return `<div class="report-preview-body"><div class="report-kpi-grid">${reportMetric('Requirements', report.length, 'Traceability rows')}${reportMetric('Linked to tests', `${linked}/${report.length}`, 'Requirements with cases', 'tone-green')}${reportMetric('JIRA links', report.filter((item) => item.jira_story_id).length, 'Story relationships', 'tone-blue')}${reportMetric('Flow links', report.reduce((total, item) => total + (item.flow_paths?.length || 0), 0), 'Path relationships', 'tone-gold')}</div><div class="report-section"><div class="report-section-heading"><div><span class="eyebrow">EVIDENCE CHAIN</span><h3>Requirement-to-test mapping</h3></div>${reportStatus(linked === report.length ? 'Fully linked' : 'Link review required', linked === report.length ? 'good' : 'attention')}</div><p class="report-lead">Each row preserves the relationship from the BRD requirement through JIRA and flow evidence to generated test cases.</p><div class="table-wrap report-table-wrap"><table class="report-table"><thead><tr><th>BRD requirement</th><th>JIRA story</th><th>Criteria</th><th>Flow paths</th><th>Test cases</th></tr></thead><tbody>${rows || '<tr><td colspan="5" class="report-empty">No traceability records available.</td></tr>'}</tbody></table></div></div></div>`;
}

function renderQualityReport(report) {
  const total = Number(report.passed || 0) + Number(report.warnings || 0) + Number(report.blocked || 0);
  return `<div class="report-preview-body"><div class="report-kpi-grid">${reportMetric('Passed', report.passed || 0, 'Cases without blocking findings', 'tone-green')}${reportMetric('Warnings', report.warnings || 0, 'Cases requiring reviewer attention', report.warnings ? 'tone-gold' : 'tone-green')}${reportMetric('Blocked', report.blocked || 0, 'Cases excluded from use', report.blocked ? 'tone-coral' : 'tone-green')}${reportMetric('Evaluated', total, 'Cases assessed by quality gates', 'tone-blue')}</div><div class="report-section"><div class="report-section-heading"><div><span class="eyebrow">QUALITY DECISION</span><h3>Validation outcome</h3></div>${reportStatus(report.blocked ? 'Export blocked for some cases' : 'No blocking cases', report.blocked ? 'attention' : 'good')}</div><div class="report-point-grid"><div class="report-point"><strong>Passed checks</strong><span>${escapeHtml(`${report.passed || 0} case${report.passed === 1 ? '' : 's'} passed the current blocking checks.`)}</span></div><div class="report-point"><strong>Reviewer attention</strong><span>${escapeHtml(`${report.warnings || 0} case${report.warnings === 1 ? '' : 's'} contain warning-level findings and should be reviewed.`)}</span></div><div class="report-point"><strong>Release rule</strong><span>Validation eligibility is not human approval. Export policy and reviewer authorization still apply.</span></div></div></div></div>`;
}

function renderReviewReport(report) {
  const entries = Object.entries(report || {});
  const needsReview = Number(report.NEEDS_REVIEW || 0);
  const approved = Number(report.APPROVED || 0);
  const clarification = Number(report.NEEDS_CLARIFICATION || 0);
  const rejected = Number(report.REJECTED || 0);
  const total = entries.reduce((sum, [, count]) => sum + Number(count), 0);
  const approvedRate = total ? Math.round((approved / total) * 100) : 0;
  const queueText = needsReview ? `${needsReview} case${needsReview === 1 ? '' : 's'} still need a human decision.` : 'The review queue is clear.';
  const approvalText = approved ? `${approved} case${approved === 1 ? '' : 's'} approved by an authorized reviewer (${approvedRate}% of the run).` : 'No cases have been approved yet.';
  const actionText = clarification ? `${clarification} case${clarification === 1 ? '' : 's'} need clarification before approval.` : rejected ? `${rejected} rejected case${rejected === 1 ? '' : 's'} should be revised or intentionally excluded.` : 'Review the remaining cases, then export according to policy.';
  return `<div class="report-preview-body"><div class="report-kpi-grid">${reportMetric('Needs review', needsReview, 'Awaiting tester decision', needsReview ? 'tone-gold' : 'tone-green')}${reportMetric('Approved', approved, 'Human-approved cases', 'tone-green')}${reportMetric('Clarification', clarification, 'Open questions', clarification ? 'tone-coral' : 'tone-green')}${reportMetric('Rejected', rejected, 'Cases not accepted', 'tone-blue')}</div><div class="report-section"><div class="report-section-heading"><div><span class="eyebrow">REVIEW SUMMARY</span><h3>Human decision status</h3></div>${reportStatus(needsReview ? 'Review in progress' : 'No pending review', needsReview ? 'attention' : 'good')}</div><div class="report-point-grid"><div class="report-point"><strong>Review queue</strong><span>${escapeHtml(queueText)}</span></div><div class="report-point"><strong>Approval progress</strong><span>${escapeHtml(approvalText)}</span></div><div class="report-point"><strong>Next action</strong><span>${escapeHtml(actionText)}</span></div></div></div><div class="report-section"><div class="report-section-heading"><div><span class="eyebrow">STATUS DISTRIBUTION</span><h3>Cases by review state</h3></div></div><div class="review-status-list">${entries.map(([status, count]) => `<div class="review-status-row"><span>${escapeHtml(status.replaceAll('_', ' '))}</span><strong>${escapeHtml(count)}</strong><div class="review-status-track"><span style="width:${total ? Math.min(Number(count) / total * 100, 100) : 0}%"></span></div></div>`).join('')}</div></div></div>`;
}

function renderChangeImpactReport(report) {
  if (!Array.isArray(report) || !report.length) return '<div class="report-preview-body"><div class="report-section report-clear-state"><span class="report-clear-icon">&#10003;</span><h3>No change impacts recorded</h3><p>No stale or broken source references are currently reported for this run.</p></div></div>';
  return `<div class="report-preview-body"><div class="report-section"><div class="report-section-heading"><div><span class="eyebrow">CHANGE REVIEW</span><h3>Cases requiring re-review</h3></div>${reportStatus('Action required', 'attention')}</div><div class="report-point-grid">${report.map((item) => `<div class="report-point"><strong>${escapeHtml(item.case_id || item.test_case_id || 'Affected case')}</strong><span>${escapeHtml(item.reason || item.message || 'Source reference changed and requires review.')}</span></div>`).join('')}</div></div></div>`;
}

function openCase(caseId) {
  const item = state.cases.find((candidate) => candidate.test_case_id === caseId);
  if (!item) return;
  selectedCaseId = caseId;
  $('#dialog-case-title').textContent = item.scenario;
  $('#dialog-case-meta').innerHTML = `<span>${escapeHtml(item.test_case_number || 'Unnumbered')}</span><span>${escapeHtml(item.requirement_id)}</span><span>${escapeHtml(item.test_type)}</span><span>${escapeHtml(item.review_status.replaceAll('_', ' '))}</span>`;
  $('#edit-scenario').value = item.scenario;
  $('#edit-priority').value = item.priority;
  $('#edit-preconditions').value = item.preconditions.join('\n');
  $('#edit-results').value = item.expected_results.join('\n');
  $('#dialog-evidence-list').innerHTML = item.source_references.map((reference) => `<div>${escapeHtml(reference.label)} · ${escapeHtml(reference.source_id)}</div>`).join('');
  $('#case-dialog').showModal();
}

async function refresh() {
  const query = activeRunId() ? `?run_id=${encodeURIComponent(activeRunId())}` : '';
  applyState(await api(`/api/state${query}`));
}

async function actionRequest(path, options, message) {
  try {
    applyState(await api(path, options));
    showFlash(message);
  } catch (error) {
    showFlash(error.message, true);
  }
}

$$('.nav-item').forEach((button) => button.addEventListener('click', () => {
  const screen = button.dataset.screen;
  $$('.nav-item').forEach((item) => item.classList.toggle('active', item === button));
  $$('.screen').forEach((item) => item.classList.toggle('active', item.id === `screen-${screen}`));
  $('#breadcrumb-label').textContent = button.textContent.trim();
  if (screen === 'cases') refresh().catch((error) => showFlash(error.message, true));
}));
$$('[data-screen-target]').forEach((button) => button.addEventListener('click', () => $(`[data-screen="${button.dataset.screenTarget}"]`).click()));
$('#sample-button').addEventListener('click', () => actionRequest('/api/demo/load', { method: 'POST' }, 'Sample evidence loaded and normalized.'));
$('#new-run-button').addEventListener('click', () => actionRequest('/api/run', jsonOptions('POST', { project_name: 'New payment review', feature_context: 'Fund transfer evidence', classification: 'INTERNAL' }), 'New generation run created.'));
$('#process-button').addEventListener('click', () => actionRequest('/api/process', jsonOptions('POST', { run_id: activeRunId() }), 'Documents processed and traceability updated.'));
$('#generate-button').addEventListener('click', async () => {
  const selected = $$('.scenario-option input:checked').map((input) => input.value);
  const button = $('#generate-button');
  if (!activeRunId()) {
    showFlash('Create or load a generation run before generating tests.', true);
    return;
  }
  if (!selected.length) {
    showFlash('Select at least one test type before generating tests.', true);
    return;
  }
  const originalLabel = button.innerHTML;
  button.disabled = true;
  button.setAttribute('aria-busy', 'true');
  button.innerHTML = 'Generating...';
  try {
    const payload = await api('/api/generate', jsonOptions('POST', { run_id: activeRunId(), test_types: selected }));
    applyState(payload);
    const summary = payload.generation || {};
    if (summary.created_cases > 0 && summary.failed_count > 0) {
      const fallbackText = summary.fallback_count ? ` ${summary.fallback_count} used the local evidence fallback and require review.` : '';
      showFlash(`${summary.created_cases} case${summary.created_cases === 1 ? '' : 's'} generated across the selected types; ${summary.failed_count} provider request${summary.failed_count === 1 ? '' : 's'} need retry.${fallbackText}`);
    } else if (summary.created_cases > 0) {
      showFlash(`${summary.created_cases} evidence-grounded case${summary.created_cases === 1 ? '' : 's'} generated.`);
    } else if (summary.failed_count > 0) {
      showFlash('No cases were generated. Provider failures were recorded; check the backend and retry.', true);
    } else {
      showFlash('No new cases were generated. The selected scenarios may already exist.');
    }
  } catch (error) {
    showFlash(error.message, true);
  } finally {
    button.disabled = false;
    button.removeAttribute('aria-busy');
    button.innerHTML = originalLabel;
  }
});
$('#validate-button').addEventListener('click', () => actionRequest('/api/validate', jsonOptions('POST', { run_id: activeRunId() }), 'Quality gates completed.'));
$('#cases-export-button').addEventListener('click', () => $(`[data-screen="reports"]`).click());
$('#select-all-types').addEventListener('click', () => $$('.scenario-option input').forEach((input) => { input.checked = true; }));
$('#case-search').addEventListener('input', renderCases);
$('#case-type-filter').addEventListener('change', renderCases);
$('#case-status-filter').addEventListener('change', renderCases);
$('#case-table').addEventListener('click', (event) => {
  const button = event.target.closest('[data-case-id]');
  if (button) openCase(button.dataset.caseId);
});
$('#upload-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  form.set('run_id', activeRunId());
  await actionRequest('/api/upload', { method: 'POST', body: form }, 'Evidence registered. Run document validation to continue.');
});
$('#save-case-button').addEventListener('click', () => {
  if (!selectedCaseId) return;
  actionRequest(`/api/cases/${selectedCaseId}`, jsonOptions('PUT', { run_id: activeRunId(), scenario: $('#edit-scenario').value, priority: $('#edit-priority').value, preconditions: $('#edit-preconditions').value.split('\n'), expected_results: $('#edit-results').value.split('\n') }), 'Case edits saved.');
  $('#case-dialog').close();
});
$('#approve-case-button').addEventListener('click', () => reviewSelected('approve'));
$('#reject-case-button').addEventListener('click', () => reviewSelected('reject'));
async function reviewSelected(action) {
  if (!selectedCaseId) return;
  const selectedCase = state.cases.find((item) => item.test_case_id === selectedCaseId);
  const priority = $('#edit-priority').value;
  await actionRequest(`/api/cases/${selectedCaseId}/review`, jsonOptions('POST', { run_id: activeRunId(), action, priority, actor: 'local-reviewer', reason: action === 'approve' ? 'Reviewed in workspace' : 'Rejected in workspace' }), action === 'approve' ? `Case ${selectedCase?.test_case_number || ''} approved with reviewer priority.` : 'Case rejected.');
  $('#case-dialog').close();
}
$$('.export-action').forEach((button) => button.addEventListener('click', async () => {
  try {
    const response = await fetch(`/api/export/${button.dataset.format}`, jsonOptions('POST', { run_id: activeRunId(), approved_only: false }));
    if (!response.ok) throw new Error('Export could not be created');
    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `test-cases.${button.dataset.format}`;
    link.click();
    URL.revokeObjectURL(link.href);
    showFlash(`${button.dataset.format.toUpperCase()} export downloaded.`);
  } catch (error) { showFlash(error.message, true); }
}));
$$('.report-link').forEach((button) => button.addEventListener('click', async () => {
  try {
    const report = await api(`/api/report/${button.dataset.report}?run_id=${encodeURIComponent(activeRunId())}`);
    activeReportType = button.dataset.report;
    $$('.report-link').forEach((item) => item.classList.toggle('selected', item === button));
    $('#report-title').textContent = reportTitle(activeReportType);
    $('#report-output').innerHTML = renderReportPreview(activeReportType, report);
  } catch (error) { showFlash(error.message, true); }
}));
$('#run-select').addEventListener('change', refresh);

refresh().catch((error) => showFlash(error.message, true));
