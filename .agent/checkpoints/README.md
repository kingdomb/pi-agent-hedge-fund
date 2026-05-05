# Checkpoint Directory
# This directory stores phase gate checkpoints for /create-req and /implement-req workflows.
# Each REQ-ID gets its own subdirectory with JSON checkpoint files.
#
# Structure:
#   .agent/checkpoints/{REQ-ID}/
#     ├── phase1_discovery.json
#     ├── phase2_draft.json
#     ├── phase3_board_review.json
#     ├── phase4_finalization.json
#     └── phase5_registration.json
#
# Checkpoints are automatically generated via CLI:
#   npm run sign-off -- --req REQ-ID --phase 1
