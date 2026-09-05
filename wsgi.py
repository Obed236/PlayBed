"""Hardened production entry point."""
from app import app
from security_hardening import apply_security

apply_security(app)
