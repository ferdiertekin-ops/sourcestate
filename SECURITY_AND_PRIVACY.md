# Security and privacy notes

SourceState v0.3 is a research prototype, not a production security product.

## Public grant demo

The public `space_app.py` is intentionally synthetic-only and accepts no arbitrary research-document uploads.

## Local research mode

The local `app.py` processes user-supplied files on the machine where the application is running. v0.3 makes no silent web or LLM calls. Temporary export files are created locally for audit JSON, CSV ledgers, and Research Receipts.

Users should not upload confidential, restricted, personal, or rights-controlled materials to a third-party deployment unless they have independently verified the deployment's storage, retention, access-control, and privacy conditions.

## Trust boundary

SourceState records the state of material supplied to it. It does not establish that a file is authentic, complete, canonical, legally reusable, or historically true.
