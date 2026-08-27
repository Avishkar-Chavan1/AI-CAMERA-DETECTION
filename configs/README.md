# Configuration directory

This directory is reserved for reviewed, non-secret, versioned configuration such as
camera-independent policy defaults and logging presets when those capabilities are
implemented. Phases 1 and 2 use environment variables only.

Keep secrets in environment variables or a deployment secret manager; never commit
them to this directory.
