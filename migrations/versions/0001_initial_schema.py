"""initial schema"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    company_status = sa.Enum(
        "active", "inactive", "rejected", "excluded", name="companystatus", native_enum=False
    )
    company_type = sa.Enum(
        "public", "pre_ipo", "private", "unknown", name="companytype", native_enum=False
    )
    review_status = sa.Enum(
        "not_reviewed", "rejected", "interested", "applied", name="reviewstatus", native_enum=False
    )
    career_status = sa.Enum(
        "active",
        "removed",
        "unknown",
        "scan_failed",
        "unsupported",
        name="careersitestatus",
        native_enum=False,
    )
    workflow_status = sa.Enum(
        "pending", "running", "succeeded", "failed", name="workflowstatus", native_enum=False
    )
    actor_type = sa.Enum("local_user", "system", name="actortype", native_enum=False)

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("careers_url", sa.String(length=500), nullable=True),
        sa.Column("ats_provider", sa.String(length=100), nullable=True),
        sa.Column("ats_company_identifier", sa.String(length=255), nullable=True),
        sa.Column("company_type", company_type, nullable=False),
        sa.Column("public_status", sa.String(length=100), nullable=True),
        sa.Column("ticker", sa.String(length=20), nullable=True),
        sa.Column("industry_tags", sa.Text(), nullable=True),
        sa.Column("product_tags", sa.Text(), nullable=True),
        sa.Column("company_description", sa.Text(), nullable=True),
        sa.Column("headquarters_location", sa.String(length=255), nullable=True),
        sa.Column("status", company_status, nullable=False),
        sa.Column("scan_block", sa.Integer(), nullable=True),
        sa.Column("scan_frequency_override", sa.String(length=100), nullable=True),
        sa.Column("seed_source", sa.String(length=255), nullable=True),
        sa.Column("seed_run_id", sa.String(length=255), nullable=True),
        sa.Column("seed_rationale", sa.Text(), nullable=True),
        sa.Column("source_urls", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("exclusion_reason", sa.Text(), nullable=True),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_scheduled_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "scan_assignment_mode",
            sa.String(length=20),
            nullable=False,
            server_default="auto",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_companies_company_type", "companies", ["company_type"])
    op.create_index("ix_companies_normalized_name", "companies", ["normalized_name"])
    op.create_index("ix_companies_scan_block", "companies", ["scan_block"])
    op.create_index("ix_companies_seed_run_id", "companies", ["seed_run_id"])
    op.create_index("ix_companies_seed_source", "companies", ["seed_source"])
    op.create_index("ix_companies_status", "companies", ["status"])
    op.create_index("ix_companies_ticker", "companies", ["ticker"])

    op.create_table(
        "company_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("normalized_alias", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
    op.create_index("ix_company_aliases_alias", "company_aliases", ["alias"])
    op.create_index("ix_company_aliases_company_id", "company_aliases", ["company_id"])
    op.create_index("ix_company_aliases_normalized_alias", "company_aliases", ["normalized_alias"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("actor_type", actor_type, nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("before_payload", sa.JSON(), nullable=True),
        sa.Column("after_payload", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
    op.create_index("ix_audit_events_actor_type", "audit_events", ["actor_type"])
    op.create_index("ix_audit_events_company_id", "audit_events", ["company_id"])
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])
    op.create_index("ix_audit_events_entity_type", "audit_events", ["entity_type"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])

    op.create_table(
        "job_postings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("external_job_id", sa.String(length=255), nullable=True),
        sa.Column("source_provider", sa.String(length=100), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("canonical_url", sa.String(length=1000), nullable=True),
        sa.Column("application_url", sa.String(length=1000), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("normalized_title", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("normalized_location", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("employment_type", sa.String(length=100), nullable=True),
        sa.Column("work_arrangement", sa.String(length=100), nullable=True),
        sa.Column("salary_text", sa.String(length=255), nullable=True),
        sa.Column("job_description_text", sa.Text(), nullable=True),
        sa.Column("job_description_hash", sa.String(length=128), nullable=True),
        sa.Column("job_summary", sa.Text(), nullable=True),
        sa.Column("fit_score", sa.Float(), nullable=True),
        sa.Column("competitiveness_score", sa.Float(), nullable=True),
        sa.Column("interest_score", sa.Float(), nullable=True),
        sa.Column("priority_score", sa.Float(), nullable=True),
        sa.Column("fit_explanation", sa.Text(), nullable=True),
        sa.Column("skill_matches", sa.Text(), nullable=True),
        sa.Column("skill_gaps", sa.Text(), nullable=True),
        sa.Column("role_family", sa.String(length=255), nullable=True),
        sa.Column("review_status", review_status, nullable=False),
        sa.Column("career_site_status", career_status, nullable=False),
        sa.Column("user_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
    op.create_index("ix_job_postings_canonical_url", "job_postings", ["canonical_url"])
    op.create_index("ix_job_postings_career_site_status", "job_postings", ["career_site_status"])
    op.create_index("ix_job_postings_company_id", "job_postings", ["company_id"])
    op.create_index("ix_job_postings_external_job_id", "job_postings", ["external_job_id"])
    op.create_index(
        "ix_job_postings_job_description_hash", "job_postings", ["job_description_hash"]
    )
    op.create_index("ix_job_postings_normalized_location", "job_postings", ["normalized_location"])
    op.create_index("ix_job_postings_normalized_title", "job_postings", ["normalized_title"])
    op.create_index("ix_job_postings_priority_score", "job_postings", ["priority_score"])
    op.create_index("ix_job_postings_review_status", "job_postings", ["review_status"])
    op.create_index("ix_job_postings_role_family", "job_postings", ["role_family"])

    op.create_table(
        "scan_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_type", sa.String(length=100), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=255), nullable=True),
        sa.Column("scope", sa.String(length=255), nullable=True),
        sa.Column("status", workflow_status, nullable=False),
        sa.Column("jobs_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_marked_removed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scan_runs_status", "scan_runs", ["status"])
    op.create_index("ix_scan_runs_workflow_run_id", "scan_runs", ["workflow_run_id"])
    op.create_index("ix_scan_runs_workflow_type", "scan_runs", ["workflow_type"])

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_name", sa.String(length=100), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=255), nullable=True),
        sa.Column("status", workflow_status, nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_runs_status", "workflow_runs", ["status"])
    op.create_index("ix_workflow_runs_workflow_name", "workflow_runs", ["workflow_name"])
    op.create_index("ix_workflow_runs_workflow_run_id", "workflow_runs", ["workflow_run_id"])

    op.create_table(
        "llm_usage_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("prompt_hash", sa.String(length=128), nullable=True),
        sa.Column("response_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_llm_usage_records_operation", "llm_usage_records", ["operation"])
    op.create_index("ix_llm_usage_records_prompt_hash", "llm_usage_records", ["prompt_hash"])
    op.create_index("ix_llm_usage_records_provider", "llm_usage_records", ["provider"])


def downgrade():
    op.drop_table("llm_usage_records")
    op.drop_table("workflow_runs")
    op.drop_table("scan_runs")
    op.drop_table("job_postings")
    op.drop_table("audit_events")
    op.drop_table("company_aliases")
    op.drop_table("companies")
