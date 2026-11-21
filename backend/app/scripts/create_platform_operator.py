from __future__ import annotations
import argparse
import asyncio
import getpass
from uuid import UUID
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.platform import PlatformOperator
from app.services.platform_operator_lifecycle import (
    ensure_another_active_owner_remains,
    lock_operator_lifecycle,
)
from app.services.platform_audit import record_platform_audit
from app.exceptions import BaseAppException


def parser():
    p = argparse.ArgumentParser(description="Manage AV platform operators")
    sub = p.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("email")
    create.add_argument("name")
    create.add_argument("--role", choices=("owner", "support"), default="support")
    for cmd in ("change-role", "reactivate-owner", "reset-mfa"):
        item = sub.add_parser(cmd)
        item.add_argument("operator_id")
    sub.choices["change-role"].add_argument("role", choices=("owner", "support"))
    return p


async def run(args):
    async with AsyncSessionLocal() as db:
        async with db.begin():
            if args.command in {"create", "change-role", "reactivate-owner"}:
                await lock_operator_lifecycle(db)
            if args.command == "create":
                password = getpass.getpass("Initial password: ")
                confirmation = getpass.getpass("Confirm password: ")
                if password != confirmation or not password:
                    raise SystemExit("Passwords do not match or are empty")
                email = args.email.strip().lower()
                if await db.scalar(select(PlatformOperator.id).where(PlatformOperator.email == email)):
                    raise SystemExit("Operator already exists")
                operator = PlatformOperator(email=email, name=args.name.strip(), role=args.role,
                                            password_hash=get_password_hash(password), mfa_secret=None,
                                            mfa_enabled=False, is_active=True)
                db.add(operator)
                await db.flush()
                record_platform_audit(db, action="cli.operator.created", target_type="operator", target_id=operator.id,
                                      details={"after": {"email": email, "name": operator.name, "role": operator.role}})
                return
            try:
                operator_id = UUID(args.operator_id)
            except ValueError:
                raise SystemExit("Invalid operator id")
            target = await db.scalar(select(PlatformOperator).where(PlatformOperator.id == operator_id).with_for_update())
            if target is None:
                raise SystemExit("Operator not found")
            before = {"role": target.role, "is_active": target.is_active, "mfa_enabled": target.mfa_enabled}
            if args.command == "change-role":
                if (
                    target.role == "owner"
                    and target.is_active
                    and args.role == "support"
                ):
                    active_owners = (
                        await db.scalars(
                            select(PlatformOperator)
                            .where(
                                PlatformOperator.role == "owner",
                                PlatformOperator.is_active.is_(True),
                            )
                            .order_by(PlatformOperator.id)
                            .with_for_update()
                        )
                    ).all()
                    ensure_another_active_owner_remains(
                        len(active_owners), action="demote"
                    )
                target.role = args.role
                target.token_version += 1
                action = "cli.operator.role_changed"
                after = {"role": target.role, "is_active": target.is_active, "mfa_enabled": target.mfa_enabled}
            elif args.command == "reactivate-owner":
                if target.role != "owner":
                    raise SystemExit("Target is not an Owner")
                target.is_active = True
                target.token_version += 1
                action = "cli.operator.owner_reactivated"
                after = {"role": target.role, "is_active": True, "mfa_enabled": target.mfa_enabled}
            else:
                target.mfa_secret = None
                target.mfa_enabled = False
                target.last_totp_step = None
                target.token_version += 1
                action = "cli.operator.mfa_reset"
                after = {"role": target.role, "is_active": target.is_active, "mfa_enabled": False}
            await db.flush()
            record_platform_audit(db, action=action, target_type="operator", target_id=target.id,
                                  details={"before": before, "after": after})


def main():
    try:
        asyncio.run(run(parser().parse_args()))
    except BaseAppException as exc:
        raise SystemExit(f"{exc.code}: {exc.message}") from exc

if __name__ == "__main__":
    main()
