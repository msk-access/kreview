#!/usr/bin/env bash
# Verify the PHI/PII guard in .gitleaks.toml works in BOTH directions.
#
# A scanner that never fires is worse than no scanner: it produces a false sense of
# safety. So this asserts three things, and fails loudly (non-zero exit + message) on
# any of them:
#
#   1. NEGATIVE — the repository working tree is clean (no PHI/secret findings).
#      Guards against a rule that false-positives and blocks every push.
#   2. POSITIVE — synthetic PHI is detected, and every rule id fires.
#      Guards against a rule that silently stops matching (typo, bad regex, over-broad
#      allowlist) and lets real PHI through.
#   3. PLACEHOLDER — the documented `P-0000000` placeholder is NOT flagged, so docs can
#      show the shape of a sample id.
#   4. CONFIG SELF-CHECK — .gitleaks.toml itself carries no real identifier. gitleaks skips
#      its own config file, so anything pasted into a comment there is invisible to the
#      scanner and would be published unnoticed. Only this script can catch it.
#
# Enforcement itself lives in .claude/hooks/gitleaks-pre-push.py (blocks `git push`) and
# in the CI secret/PHI scan. This script validates the rules those rely on.
#
# Usage:  bash scripts/check_phi_guard.sh
# Exit:   0 = guard healthy, 1 = guard broken (message explains which assertion failed)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$REPO_ROOT/.gitleaks.toml"

# Every rule id defined in .gitleaks.toml that the positive probe must trigger.
EXPECTED_RULES="date-of-birth medical-record-number msk-dmp-patient-id us-ssn"

fail() { echo "FAIL: $*" >&2; exit 1; }

command -v gitleaks >/dev/null 2>&1 \
  || fail "gitleaks is not installed (brew install gitleaks). The PHI guard cannot be verified."
[ -f "$CONFIG" ] || fail "missing $CONFIG"

TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }   # probe files never touch the repo tree
trap cleanup EXIT

echo "PHI guard check — config: $CONFIG"

# ── 1. NEGATIVE: the working tree must be clean ────────────────────────────────
echo "  [1/4] repository tree is clean ..."
if ! gitleaks detect --source "$REPO_ROOT" --no-git --no-banner --redact >/dev/null 2>&1; then
  fail "the repository tree has PHI/secret findings, or a rule is false-positiving.
       Run: gitleaks detect --source . --no-git --redact"
fi
echo "        OK — no findings"

# ── 2. POSITIVE: synthetic PHI must be detected by every rule ──────────────────
echo "  [2/4] synthetic PHI is detected ..."
# The probe values are assembled at RUNTIME from fragments on purpose: if the literal
# patterns appeared in this file, the guard would (correctly) flag this script itself and
# block the push. Building them here keeps the guard strict — no path exemption needed.
probe_pid="$(printf 'P-%s' 1234567)"
probe_ssn="$(printf '%s-%s-%s' 123 45 6789)"
probe_mrn="$(printf 'MRN: %s' 9876543)"
probe_dob="$(printf 'DOB: %s/%s/%s' 03 14 1972)"

cat > "$TMP/probe.md" <<PROBE
Patient ${probe_pid}-T01-IM6 consented on study.
SSN: ${probe_ssn}
${probe_mrn}
${probe_dob}
PROBE

# gitleaks exits non-zero when it finds leaks, which is the expected outcome here.
gitleaks detect --source "$TMP" --no-git --no-banner --redact -c "$CONFIG" \
  --report-format json --report-path "$TMP/report.json" >/dev/null 2>&1 || true

[ -s "$TMP/report.json" ] \
  || fail "synthetic PHI was NOT detected — the guard is not working. Check the rules in $CONFIG."

FIRED="$(python3 -c "
import json
print(' '.join(sorted({x['RuleID'] for x in json.load(open('$TMP/report.json'))})))
")"
for rule in $EXPECTED_RULES; do
  case " $FIRED " in
    *" $rule "*) ;;
    *) fail "rule '$rule' did not fire on the probe (fired: ${FIRED:-none}). Regex or allowlist is broken." ;;
  esac
done
echo "        OK — all rules fired: $FIRED"

# ── 3. PLACEHOLDER: the documented example id must be allowed ──────────────────
echo "  [3/4] P-0000000 placeholder is allowed ..."
rm -f "$TMP/probe.md" "$TMP/report.json"
printf 'Example: P-0000000-T01-XS1.FSC.gene.parquet\n' > "$TMP/placeholder.md"
if ! gitleaks detect --source "$TMP" --no-git --no-banner --redact -c "$CONFIG" >/dev/null 2>&1; then
  fail "the P-0000000 placeholder is being flagged — docs cannot show a sample id shape.
       Check the [allowlist] regexes in $CONFIG."
fi
echo "        OK — placeholder not flagged"

# ── 4. CONFIG SELF-CHECK: .gitleaks.toml must contain no real identifiers ──────
# gitleaks refuses to scan its own config, so copy it under a different name and scan that.
echo "  [4/4] .gitleaks.toml carries no real identifiers ..."
cp "$CONFIG" "$TMP/config-copy.txt"
if ! gitleaks detect --source "$TMP" --no-git --no-banner --redact -c "$CONFIG" >/dev/null 2>&1; then
  fail "a real identifier appears inside .gitleaks.toml. gitleaks does NOT scan its own
       config, so this would be published unnoticed. Refer to commits by SHA, never by value."
fi
echo "        OK — config clean"

echo "PHI guard healthy: tree clean, all rules fire, placeholder allowed, config clean."
