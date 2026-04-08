import os
from pathlib import Path

# The safe local target path
TARGET = Path("/Users/shahr2/data_temp/unified_krewlyzer_results")
TARGET.mkdir(parents=True, exist_ok=True)

# The mounted SFTP paths containing fragmentomics results
# Notice the EN-DASH (–) in the remote path matching your specific duck.app mount exactly.
BASE_MOUNT = Path(
    "/Users/shahr2/Library/Group Containers/G69SCX94XU.duck/Library/Application Support/duck/Volumes.noindex/shahr2 - islogin01.mskcc.org – SFTP/share/krewlyzer/0.8.2"
)

SOURCES = [
    BASE_MOUNT / "access_12_245/results",
    BASE_MOUNT / "healthy_controls/xs1/results",
    BASE_MOUNT / "healthy_controls/xs2/results",
]

total_linked = 0
total_skipped = 0

for src_path in SOURCES:
    if not src_path.exists():
        print(f"[!] Skipping missing source path: {src_path}")
        continue

    print(f"\n[*] Scanning: {src_path}")

    # Iterate through every folder inside the results directory
    for sample_dir in src_path.iterdir():
        if sample_dir.is_dir():
            dest = TARGET / sample_dir.name

            # If the symlink doesn't exist locally, create it
            if not dest.exists():
                os.symlink(sample_dir, dest)
                total_linked += 1
            else:
                total_skipped += 1

print("\n" + "=" * 50)
print("✅ Sync Complete!")
print(f"📊 Newly Linked Samples: {total_linked}")
print(f"⏭️  Already Existed: {total_skipped}")
print(f"📁 Target Directory: {TARGET}")
print("=" * 50)
