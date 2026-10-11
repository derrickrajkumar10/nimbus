#!/usr/bin/env bash
# Regenerate everything derived from the Pydantic models. Run after any contract change.
set -euo pipefail
cd "$(dirname "$0")"
export UV_LINK_MODE=copy

uv run python tools/export_schema.py
uv run python tools/build_fixtures.py

npx -y json-schema-to-typescript@15 -i schema/nimbus.schema.json -o generated/ts/nimbus.ts \
  --unreachableDefinitions --additionalProperties false \
  --bannerComment "/* Generated from contracts/schema/nimbus.schema.json. Do not edit; run contracts/generate.sh. */"

defs=()
for m in Segment SegmentRisk Report Reading Hazard Sos RankedSos SavedPlace Resource Proposal Alert RouteRequest RouteResponse; do
  defs+=("schema/nimbus.schema.json#/\$defs/$m")
done
npx -y quicktype@23 -s schema -l dart --null-safety --required-props -o generated/dart/nimbus.dart "${defs[@]}"

uv run pytest -q
