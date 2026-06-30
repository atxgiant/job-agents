"""phase 3 job lifecycle"""

import sqlalchemy as sa
from alembic import op

revision = "0002_phase3_job_lifecycle"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    scan_run_status = sa.Enum(
        "pending",
        "running",
        "completed",
        "completed_with_warnings",
        "failed",
        "unsupported",
        name="scanrunstatus",
        native_enum=False,
    )
    scan_type = sa.Enum("manual_greenhouse", name="scantype", native_enum=False)

    with op.batch_alter_table("job_postings") as batch_op:
        batch_op.add_column(sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "career_site_status_changed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("rejection_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("provider_metadata_json", sa.JSON(), nullable=True))
        batch_op.drop_column("fit_score")
        batch_op.drop_column("competitiveness_score")
        batch_op.drop_column("interest_score")
        batch_op.drop_column("priority_score")
        batch_op.drop_column("fit_explanation")
        batch_op.drop_column("skill_matches")
        batch_op.drop_column("skill_gaps")
        batch_op.drop_column("role_family")

    op.execute("UPDATE job_postings SET first_seen_at = created_at WHERE first_seen_at IS NULL")
    op.execute("UPDATE job_postings SET last_seen_at = created_at WHERE last_seen_at IS NULL")
    op.execute(
        "UPDATE job_postings SET last_verified_at = created_at WHERE last_verified_at IS NULL"
    )
    op.execute(
        "UPDATE job_postings SET career_site_status_changed_at = created_at "
        "WHERE career_site_status_changed_at IS NULL"
    )

    with op.batch_alter_table("job_postings") as batch_op:
        batch_op.alter_column("first_seen_at", nullable=False)
        batch_op.alter_column("last_seen_at", nullable=False)
        batch_op.alter_column("last_verified_at", nullable=False)
        batch_op.alter_column("career_site_status_changed_at", nullable=False)

    with op.batch_alter_table("scan_runs") as batch_op:
        batch_op.add_column(sa.Column("company_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("scan_type", scan_type, nullable=True))
        batch_op.add_column(sa.Column("source_provider", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column("jobs_discovered_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("jobs_created_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("jobs_updated_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column(
                "jobs_marked_removed_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(sa.Column("error_code", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("error_message", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("request_metadata_json", sa.JSON(), nullable=True))
        batch_op.drop_column("workflow_type")
        batch_op.drop_column("workflow_run_id")
        batch_op.drop_column("scope")
        batch_op.drop_column("jobs_discovered")
        batch_op.drop_column("jobs_updated")
        batch_op.drop_column("jobs_marked_removed")
        batch_op.drop_column("errors")
        batch_op.alter_column("status", existing_type=sa.String(length=23), type_=scan_run_status)
        batch_op.create_foreign_key(
            "fk_scan_runs_company_id_companies", "companies", ["company_id"], ["id"]
        )

    op.execute("UPDATE scan_runs SET scan_type = 'manual_greenhouse' WHERE scan_type IS NULL")
    with op.batch_alter_table("scan_runs") as batch_op:
        batch_op.alter_column("scan_type", nullable=False)

    op.create_index("ix_scan_runs_company_id", "scan_runs", ["company_id"])
    op.create_index("ix_scan_runs_scan_type", "scan_runs", ["scan_type"])
    op.create_index("ix_scan_runs_source_provider", "scan_runs", ["source_provider"])

    op.create_table(
        "job_scan_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_posting_id", sa.Integer(), nullable=False),
        sa.Column("scan_run_id", sa.Integer(), nullable=False),
        sa.Column("observed_status", sa.String(length=12), nullable=False),
        sa.Column("source_payload_hash", sa.String(length=128), nullable=True),
        sa.Column("title_snapshot", sa.String(length=255), nullable=True),
        sa.Column("location_snapshot", sa.String(length=255), nullable=True),
        sa.Column("department_snapshot", sa.String(length=255), nullable=True),
        sa.Column("description_hash_snapshot", sa.String(length=128), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_posting_id"], ["job_postings.id"]),
        sa.ForeignKeyConstraint(["scan_run_id"], ["scan_runs.id"]),
    )
    op.create_index(
        "ix_job_scan_observations_job_posting_id", "job_scan_observations", ["job_posting_id"]
    )
    op.create_index(
        "ix_job_scan_observations_scan_run_id", "job_scan_observations", ["scan_run_id"]
    )

    op.create_table(
        "job_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_posting_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("actor_type", sa.String(length=10), nullable=False),
        sa.Column("previous_review_status", sa.String(length=12), nullable=True),
        sa.Column("new_review_status", sa.String(length=12), nullable=True),
        sa.Column("previous_career_site_status", sa.String(length=12), nullable=True),
        sa.Column("new_career_site_status", sa.String(length=12), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_posting_id"], ["job_postings.id"]),
    )
    op.create_index(
        "ix_job_status_history_job_posting_id", "job_status_history", ["job_posting_id"]
    )
    op.create_index("ix_job_status_history_event_type", "job_status_history", ["event_type"])
    op.create_index("ix_job_status_history_actor_type", "job_status_history", ["actor_type"])


def downgrade():
    op.drop_table("job_status_history")
    op.drop_table("job_scan_observations")
    op.drop_index("ix_scan_runs_source_provider", table_name="scan_runs")
    op.drop_index("ix_scan_runs_scan_type", table_name="scan_runs")
    op.drop_index("ix_scan_runs_company_id", table_name="scan_runs")
    op.drop_column("scan_runs", "request_metadata_json")
    op.drop_column("scan_runs", "error_message")
    op.drop_column("scan_runs", "error_code")
    op.drop_column("scan_runs", "jobs_marked_removed_count")
    op.drop_column("scan_runs", "jobs_updated_count")
    op.drop_column("scan_runs", "jobs_created_count")
    op.drop_column("scan_runs", "jobs_discovered_count")
    op.drop_column("scan_runs", "completed_at")
    op.drop_column("scan_runs", "started_at")
    op.drop_column("scan_runs", "source_provider")
    op.drop_column("scan_runs", "scan_type")
    op.drop_column("scan_runs", "company_id")
    op.drop_column("job_postings", "provider_metadata_json")
    op.drop_column("job_postings", "rejection_reason")
    op.drop_column("job_postings", "rejected_at")
    op.drop_column("job_postings", "applied_at")
    op.drop_column("job_postings", "reviewed_at")
    op.drop_column("job_postings", "career_site_status_changed_at")
    op.drop_column("job_postings", "last_verified_at")
    op.drop_column("job_postings", "last_seen_at")
    op.drop_column("job_postings", "first_seen_at")
    op.drop_column("job_postings", "posted_at")
