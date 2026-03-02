"""初期スキーマ - 全テーブル作成（月次パーティション対応）

Revision ID: 001
Revises:
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────
    # Teams テーブル
    # ─────────────────────────────────────────────────
    op.create_table(
        'teams',
        sa.Column('team_id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('team_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.UniqueConstraint('team_name', name='uq_teams_team_name'),
    )

    # ─────────────────────────────────────────────────
    # Users テーブル
    # ─────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('user_id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(200)),
        sa.Column('role', sa.String(50), nullable=False, server_default='Viewer'),
        sa.Column('team_id', UUID(as_uuid=True),
                  sa.ForeignKey('teams.team_id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
        sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.UniqueConstraint('username', name='uq_users_username'),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_email', 'users', ['email'])

    # ─────────────────────────────────────────────────
    # Incidents テーブル（月次パーティション）
    # ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE incidents (
            incident_id UUID NOT NULL DEFAULT gen_random_uuid(),
            incident_number VARCHAR(20) NOT NULL,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            priority VARCHAR(5) NOT NULL DEFAULT 'P3',
            status VARCHAR(30) NOT NULL DEFAULT 'New',
            assigned_to UUID REFERENCES users(user_id),
            assigned_team_id UUID REFERENCES teams(team_id),
            reported_by UUID REFERENCES users(user_id),
            acknowledged_at TIMESTAMPTZ,
            resolved_at TIMESTAMPTZ,
            closed_at TIMESTAMPTZ,
            sla_response_due_at TIMESTAMPTZ,
            sla_resolution_due_at TIMESTAMPTZ,
            sla_breached BOOLEAN NOT NULL DEFAULT FALSE,
            category VARCHAR(100),
            subcategory VARCHAR(100),
            affected_service VARCHAR(200),
            resolution_notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_incident_priority CHECK (priority IN ('P1','P2','P3','P4')),
            CONSTRAINT chk_incident_status CHECK (
                status IN ('New','Acknowledged','In_Progress','Pending',
                          'Workaround_Applied','Resolved','Closed')
            ),
            CONSTRAINT chk_incident_acknowledged_at
                CHECK (acknowledged_at IS NULL OR acknowledged_at >= created_at),
            CONSTRAINT chk_incident_closed_at
                CHECK (closed_at IS NULL OR resolved_at IS NULL OR closed_at >= resolved_at)
        ) PARTITION BY RANGE (created_at)
    """)
    op.execute("CREATE UNIQUE INDEX uq_incidents_number ON incidents(incident_number)")
    op.execute("CREATE INDEX ix_incidents_status ON incidents(status)")
    op.execute("CREATE INDEX ix_incidents_priority ON incidents(priority)")
    op.execute("CREATE INDEX ix_incidents_created_at ON incidents(created_at)")
    # 初期月次パーティション（2026年）
    op.execute("""
        CREATE TABLE incidents_2026_01 PARTITION OF incidents
            FOR VALUES FROM ('2026-01-01') TO ('2026-02-01')
    """)
    op.execute("""
        CREATE TABLE incidents_2026_02 PARTITION OF incidents
            FOR VALUES FROM ('2026-02-01') TO ('2026-03-01')
    """)
    op.execute("""
        CREATE TABLE incidents_2026_03 PARTITION OF incidents
            FOR VALUES FROM ('2026-03-01') TO ('2026-04-01')
    """)
    op.execute("""
        CREATE TABLE incidents_2026_04 PARTITION OF incidents
            FOR VALUES FROM ('2026-04-01') TO ('2026-05-01')
    """)
    op.execute("""
        CREATE TABLE incidents_2026_05 PARTITION OF incidents
            FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')
    """)
    op.execute("""
        CREATE TABLE incidents_2026_06 PARTITION OF incidents
            FOR VALUES FROM ('2026-06-01') TO ('2026-07-01')
    """)
    op.execute("""
        CREATE TABLE incidents_2026_07 PARTITION OF incidents
            FOR VALUES FROM ('2026-07-01') TO ('2026-08-01')
    """)
    op.execute("""
        CREATE TABLE incidents_2026_08 PARTITION OF incidents
            FOR VALUES FROM ('2026-08-01') TO ('2026-09-01')
    """)
    op.execute("""
        CREATE TABLE incidents_2026_09 PARTITION OF incidents
            FOR VALUES FROM ('2026-09-01') TO ('2026-10-01')
    """)
    op.execute("""
        CREATE TABLE incidents_2026_10 PARTITION OF incidents
            FOR VALUES FROM ('2026-10-01') TO ('2026-11-01')
    """)
    op.execute("""
        CREATE TABLE incidents_2026_11 PARTITION OF incidents
            FOR VALUES FROM ('2026-11-01') TO ('2026-12-01')
    """)
    op.execute("""
        CREATE TABLE incidents_2026_12 PARTITION OF incidents
            FOR VALUES FROM ('2026-12-01') TO ('2027-01-01')
    """)

    # ─────────────────────────────────────────────────
    # Changes テーブル（月次パーティション）
    # ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE changes (
            change_id UUID NOT NULL DEFAULT gen_random_uuid(),
            change_number VARCHAR(20) NOT NULL,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            change_type VARCHAR(20) NOT NULL DEFAULT 'Normal',
            status VARCHAR(30) NOT NULL DEFAULT 'Draft',
            risk_score INTEGER NOT NULL DEFAULT 0,
            risk_level VARCHAR(20),
            impact_level VARCHAR(20),
            urgency_level VARCHAR(20),
            requested_by UUID REFERENCES users(user_id),
            assigned_to UUID REFERENCES users(user_id),
            cab_approved_by UUID REFERENCES users(user_id),
            scheduled_start_at TIMESTAMPTZ,
            scheduled_end_at TIMESTAMPTZ,
            actual_start_at TIMESTAMPTZ,
            actual_end_at TIMESTAMPTZ,
            cab_reviewed_at TIMESTAMPTZ,
            implementation_plan TEXT,
            rollback_plan TEXT,
            test_plan TEXT,
            cab_notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_change_type CHECK (
                change_type IN ('Standard','Normal','Emergency','Major')
            ),
            CONSTRAINT chk_change_status CHECK (
                status IN ('Draft','Submitted','CAB_Review','Approved','Rejected',
                          'Scheduled','In_Progress','Completed','Cancelled','Failed')
            ),
            CONSTRAINT chk_change_risk_score CHECK (risk_score >= 0 AND risk_score <= 100)
        ) PARTITION BY RANGE (created_at)
    """)
    op.execute("CREATE UNIQUE INDEX uq_changes_number ON changes(change_number)")
    op.execute("CREATE INDEX ix_changes_status ON changes(status)")
    op.execute("CREATE INDEX ix_changes_created_at ON changes(created_at)")
    # 2026年月次パーティション
    for month in range(1, 13):
        year = 2026
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        op.execute(f"""
            CREATE TABLE changes_{year}_{month:02d} PARTITION OF changes
                FOR VALUES FROM ('{year}-{month:02d}-01') TO ('{next_year}-{next_month:02d}-01')
        """)

    # ─────────────────────────────────────────────────
    # Problems テーブル
    # ─────────────────────────────────────────────────
    op.create_table(
        'problems',
        sa.Column('problem_id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('problem_number', sa.String(20), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('root_cause', sa.Text()),
        sa.Column('status', sa.String(30), nullable=False, server_default='New'),
        sa.Column('priority', sa.String(5), nullable=False, server_default='P3'),
        sa.Column('known_error', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('workaround', sa.Text()),
        sa.Column('assigned_to', UUID(as_uuid=True),
                  sa.ForeignKey('users.user_id'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('closed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.UniqueConstraint('problem_number', name='uq_problems_number'),
        sa.CheckConstraint(
            "status IN ('New','Under_Investigation','Known_Error','Resolved','Closed')",
            name='chk_problem_status'
        ),
    )
    op.create_index('ix_problems_number', 'problems', ['problem_number'])

    # ─────────────────────────────────────────────────
    # Service Requests テーブル
    # ─────────────────────────────────────────────────
    op.create_table(
        'service_requests',
        sa.Column('request_id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('request_number', sa.String(20), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('status', sa.String(30), nullable=False, server_default='New'),
        sa.Column('request_type', sa.String(100)),
        sa.Column('requested_by', UUID(as_uuid=True),
                  sa.ForeignKey('users.user_id'), nullable=True),
        sa.Column('assigned_to', UUID(as_uuid=True),
                  sa.ForeignKey('users.user_id'), nullable=True),
        sa.Column('approved_by', UUID(as_uuid=True),
                  sa.ForeignKey('users.user_id'), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True)),
        sa.Column('fulfilled_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.UniqueConstraint('request_number', name='uq_sr_number'),
        sa.CheckConstraint(
            "status IN ('New','Pending_Approval','Approved','In_Progress','Fulfilled','Rejected','Cancelled')",
            name='chk_sr_status'
        ),
    )

    # ─────────────────────────────────────────────────
    # Configuration Items テーブル
    # ─────────────────────────────────────────────────
    op.create_table(
        'configuration_items',
        sa.Column('ci_id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('ci_name', sa.String(200), nullable=False),
        sa.Column('ci_type', sa.String(100), nullable=False),
        sa.Column('ci_class', sa.String(100)),
        sa.Column('status', sa.String(30), nullable=False, server_default='Active'),
        sa.Column('version', sa.String(50)),
        sa.Column('owner_id', UUID(as_uuid=True),
                  sa.ForeignKey('users.user_id'), nullable=True),
        sa.Column('description', sa.Text()),
        sa.Column('attributes', JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.CheckConstraint(
            "status IN ('Active','Inactive','Maintenance','Retired')",
            name='chk_ci_status'
        ),
    )
    op.create_index('ix_ci_name', 'configuration_items', ['ci_name'])

    # ─────────────────────────────────────────────────
    # CI Relationships テーブル
    # ─────────────────────────────────────────────────
    op.create_table(
        'ci_relationships',
        sa.Column('relationship_id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_ci_id', UUID(as_uuid=True),
                  sa.ForeignKey('configuration_items.ci_id'), nullable=False),
        sa.Column('target_ci_id', UUID(as_uuid=True),
                  sa.ForeignKey('configuration_items.ci_id'), nullable=False),
        sa.Column('relationship_type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )

    # ─────────────────────────────────────────────────
    # Audit Logs テーブル（月次パーティション + SHA-256ハッシュチェーン）
    # ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE audit_logs (
            log_id UUID NOT NULL DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL,
            user_id UUID REFERENCES users(user_id),
            username VARCHAR(50),
            user_role VARCHAR(50),
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(100),
            resource_id VARCHAR(100),
            http_method VARCHAR(10),
            request_path VARCHAR(500),
            request_body JSONB,
            response_status INTEGER,
            ip_address VARCHAR(45),
            user_agent VARCHAR(500),
            old_values JSONB,
            new_values JSONB,
            prev_log_hash VARCHAR(64),
            current_hash VARCHAR(64) NOT NULL,
            sequence_number INTEGER NOT NULL
        ) PARTITION BY RANGE (created_at)
    """)
    op.execute("CREATE INDEX ix_audit_logs_created_at ON audit_logs(created_at)")
    op.execute("CREATE INDEX ix_audit_logs_sequence ON audit_logs(sequence_number)")
    op.execute("CREATE INDEX ix_audit_logs_user_id ON audit_logs(user_id)")
    # 2026年月次パーティション
    for month in range(1, 13):
        year = 2026
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        op.execute(f"""
            CREATE TABLE audit_logs_{year}_{month:02d} PARTITION OF audit_logs
                FOR VALUES FROM ('{year}-{month:02d}-01') TO ('{next_year}-{next_month:02d}-01')
        """)

    # ─────────────────────────────────────────────────
    # AI Audit Logs テーブル（月次パーティション）
    # ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ai_audit_logs (
            ai_log_id UUID NOT NULL DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL,
            agent_id VARCHAR(100) NOT NULL,
            agent_type VARCHAR(50),
            autonomy_level VARCHAR(5),
            decision_type VARCHAR(100) NOT NULL,
            decision_input JSONB,
            decision_output JSONB,
            confidence_score DECIMAL(5,4),
            human_approved BOOLEAN,
            approved_by UUID REFERENCES users(user_id),
            approval_notes TEXT,
            integrity_hash VARCHAR(64) NOT NULL
        ) PARTITION BY RANGE (created_at)
    """)
    op.execute("CREATE INDEX ix_ai_audit_logs_created_at ON ai_audit_logs(created_at)")
    for month in range(1, 13):
        year = 2026
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        op.execute(f"""
            CREATE TABLE ai_audit_logs_{year}_{month:02d} PARTITION OF ai_audit_logs
                FOR VALUES FROM ('{year}-{month:02d}-01') TO ('{next_year}-{next_month:02d}-01')
        """)

    # ─────────────────────────────────────────────────
    # Audit Log Integrity テーブル
    # ─────────────────────────────────────────────────
    op.create_table(
        'audit_log_integrity',
        sa.Column('integrity_id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified_by', UUID(as_uuid=True),
                  sa.ForeignKey('users.user_id'), nullable=True),
        sa.Column('start_sequence', sa.Integer(), nullable=False),
        sa.Column('end_sequence', sa.Integer(), nullable=False),
        sa.Column('is_valid', sa.Boolean(), nullable=False),
        sa.Column('broken_at_sequence', sa.Integer()),
        sa.Column('verification_notes', sa.Text()),
    )

    # ─────────────────────────────────────────────────
    # シーケンス（ID採番）
    # ─────────────────────────────────────────────────
    op.execute("CREATE SEQUENCE IF NOT EXISTS incident_seq START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS change_seq START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS problem_seq START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS service_request_seq START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS audit_log_seq START 1")


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS audit_log_seq")
    op.execute("DROP SEQUENCE IF EXISTS service_request_seq")
    op.execute("DROP SEQUENCE IF EXISTS problem_seq")
    op.execute("DROP SEQUENCE IF EXISTS change_seq")
    op.execute("DROP SEQUENCE IF EXISTS incident_seq")
    op.drop_table('audit_log_integrity')
    op.execute("DROP TABLE IF EXISTS ai_audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    op.drop_table('ci_relationships')
    op.drop_table('configuration_items')
    op.drop_table('service_requests')
    op.drop_table('problems')
    op.execute("DROP TABLE IF EXISTS changes CASCADE")
    op.execute("DROP TABLE IF EXISTS incidents CASCADE")
    op.drop_table('users')
    op.drop_table('teams')
