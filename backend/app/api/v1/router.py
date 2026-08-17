"""Aggregates every v1 router into a single APIRouter mounted by main.py."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.audit.router import router as audit_router
from app.api.v1.auth.router import router as auth_router
from app.api.v1.aws.router import router as aws_router
from app.api.v1.chat.router import router as chat_router
from app.api.v1.compliance.router import router as compliance_router
from app.api.v1.dashboard.router import router as dashboard_router
from app.api.v1.findings.router import router as findings_router
from app.api.v1.investigations.router import router as investigations_router
from app.api.v1.profile_settings_router import router as profile_settings_router
from app.api.v1.reports.router import router as reports_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(aws_router)
api_router.include_router(audit_router)
api_router.include_router(investigations_router)
api_router.include_router(findings_router)
api_router.include_router(compliance_router)
api_router.include_router(reports_router)
api_router.include_router(chat_router)
api_router.include_router(dashboard_router)
api_router.include_router(profile_settings_router)
