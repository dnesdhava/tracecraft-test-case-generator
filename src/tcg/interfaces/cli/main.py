from __future__ import annotations

import json
from pathlib import Path

import click

from tcg.application.pipeline import GeneratorPipeline, PipelineError
from tcg.config.settings import load_settings
from tcg.domain.models import TestType


def _pipeline() -> GeneratorPipeline:
    return GeneratorPipeline(load_settings(Path.cwd()))


@click.group()
def cli() -> None:
    """Generate evidence-grounded test cases from project sources."""


@cli.group()
def run() -> None:
    """Create and inspect generation runs."""


@run.command("create")
@click.option("--project", required=True)
@click.option("--classification", default="INTERNAL", show_default=True)
def create_run(project: str, classification: str) -> None:
    """Create a local generation run."""
    try:
        result = _pipeline().create_run(project, "", classification)
    except PipelineError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(result.run_id)


@run.command("status")
@click.option("--run-id", required=True)
def run_status(run_id: str) -> None:
    """Print a run summary."""
    try:
        result = _pipeline().get_run(run_id)
    except PipelineError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        json.dumps(
            {
                "run_id": result.run_id,
                "status": result.status.value,
                "sources": len(result.sources),
                "requirements": len(result.requirements),
                "cases": len(result.cases),
            },
            indent=2,
        )
    )


@cli.command("demo")
def demo() -> None:
    """Load the repository sample set and generate validated cases."""
    pipeline = _pipeline()
    root = pipeline.settings.project_root / "samples"
    try:
        run_state = pipeline.create_run("Demo Bank Payments", "Sample fund transfer", "INTERNAL")
        pipeline.ingest_file(run_state.run_id, root / "brd" / "sample_brd.xlsx", "brd")
        pipeline.ingest_jira_text(
            run_state.run_id,
            (root / "jira" / "sample_jira_user_story.md").read_text(encoding="utf-8"),
        )
        pipeline.ingest_file(
            run_state.run_id, root / "flow_diagrams" / "sample_payment_flow.pdf", "flow"
        )
        pipeline.process(run_state.run_id)
        pipeline.generate(run_state.run_id, set(TestType))
        result = pipeline.validate_cases(run_state.run_id)
    except (OSError, PipelineError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, indent=2))


@cli.command("generate")
@click.option("--run-id", required=True)
@click.option(
    "--test-type", "test_types", multiple=True, type=click.Choice([item.value for item in TestType])
)
def generate(run_id: str, test_types: tuple[str, ...]) -> None:
    """Generate selected scenario classes for a run."""
    pipeline = _pipeline()
    selected = {TestType(value) for value in test_types} or set(TestType)
    try:
        result = pipeline.generate(run_id, selected)
    except PipelineError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps({"run_id": result.run_id, "cases": len(result.cases)}, indent=2))


@cli.command("validate")
@click.option("--run-id", required=True)
def validate(run_id: str) -> None:
    """Run deterministic quality gates."""
    try:
        result = _pipeline().validate_cases(run_id)
    except PipelineError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, indent=2))


@cli.command("report")
@click.option("--run-id", required=True)
@click.option(
    "--report-type",
    default="summary",
    type=click.Choice(
        ["summary", "traceability", "coverage", "quality", "review", "change_impact"]
    ),
)
def report(run_id: str, report_type: str) -> None:
    """Print a non-sensitive report as JSON."""
    try:
        result = _pipeline().reports(run_id)[report_type]
    except (PipelineError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    cli()
