#!/usr/bin/env bash
# Copy the generated Dart models and the fixtures from contracts/ into the app.
# Flutter assets can't live outside the package, so the app keeps copies, and
# test/contracts_test.dart fails when they go stale. Re-run this after any
# contracts/generate.sh.
#
# The app needs nullable fields (`int? minutesToFlood;`) from PR #61. While the
# working tree's nimbus.dart predates it, the models come from CONTRACTS_REF.
set -euo pipefail
cd "$(dirname "$0")/.."

src=../contracts
ref="${CONTRACTS_REF:-origin/derrick/contracts-dart-nullable}"

mkdir -p lib/contracts assets/fixtures
if grep -q 'int? minutesToFlood;' "$src/generated/dart/nimbus.dart"; then
  cp "$src/generated/dart/nimbus.dart" lib/contracts/nimbus.dart
else
  echo "contracts/generated/dart/nimbus.dart predates #61; using $ref" >&2
  git show "$ref:contracts/generated/dart/nimbus.dart" > lib/contracts/nimbus.dart
fi

rm -f assets/fixtures/*.json
cp "$src"/fixtures/*.json assets/fixtures/
echo "synced lib/contracts/nimbus.dart and $(ls assets/fixtures | wc -l) fixtures"
