#!/usr/bin/env python3
import aws_cdk as cdk
from asterisk_pbx_stack import AsteriskPbxStack

app = cdk.App()
AsteriskPbxStack(
    app, "AsteriskPbxStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account") or None,
        region=app.node.try_get_context("region") or "us-east-1",
    ),
)

app.synth()

