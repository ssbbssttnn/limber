#!/usr/bin/env python3
"""
Limber photo cleanup.

Removes two kinds of photo files from photos/:
  1. ORPHANS  - any photos/<id>.<ext> whose <id> is no longer a stretch in
                index.html (auto-detected, self-correcting; catches every
                removed exercise now and in future).
  2. WRONG    - an explicit list of ids whose photo was flagged "wrong photo"
                during review. These stretches still exist, but their image
                was incorrect, so the photo is removed (leaving the stretch
                to show the "no photo" placeholder until a correct one is added).

Usage:
  python cleanup_photos.py            # delete + write report
  python cleanup_photos.py --dry-run  # list what WOULD be deleted, delete nothing

Env (set by the GitHub Action inputs):
  DRY_RUN=true|false
"""
import os, re, sys, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ROOT, "index.html")
PHOTOS_DIR = os.path.join(ROOT, "photos")
REPORT = os.path.join(ROOT, "cleanup-report.txt")
EXTS = ("jpg", "jpeg", "png", "webp")

# Photos flagged "wrong" during the review pass. These stretches still exist;
# only their (incorrect) photo is removed so a correct one can be added later.
WRONG_PHOTO_IDS = [
    "abdominal-stretch", "adductor", "bent-over-twist", "bridge", "cat-pose",
    "chair-pose", "corpse", "crocodile", "finger-flexor", "flexion-extension-hip",
    "frog-rock", "garland", "gate-pose", "half-seated-leg-circle", "hawaiian-squat",
    "hero", "humble-warrior", "lying-hip-flexor", "lying-lower-back", "pretzel",
    "pyramid", "reverse-warrior", "runners-stretch", "seated-ankle",
    "seated-lower-back", "seated-neck-side", "standing-iliotibial",
    "standing-leg-cross-abductor", "standing-side-bend", "thoracic-bridge",
    "warrior-1", "warrior-2", "warrior-3", "wrist-extensor", "wrist-flexor",
]

DRY_RUN = ("--dry-run" in sys.argv) or (os.environ.get("DRY_RUN", "").lower() == "true")


def live_ids():
    """Parse index.html and return the set of stretch ids currently in the library."""
    with open(INDEX, encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"<script>([\s\S]*?)</script>", html)
    script = m.group(1) if m else html
    # match the DEFAULTS objects: {id:"...",
    ids = set(re.findall(r'\{id:"([a-z0-9-]+)",', script))
    return ids


def photo_id(path):
    """photos/foo-bar.jpg -> foo-bar"""
    base = os.path.basename(path)
    return re.sub(r"\.(jpg|jpeg|png|webp)$", "", base, flags=re.I)


def main():
    if not os.path.isdir(PHOTOS_DIR):
        print("No photos/ directory found - nothing to do.")
        # still write an empty report so the workflow has something to read
        open(REPORT, "w").write("No photos/ directory found.\n")
        return

    ids = live_ids()
    if not ids:
        print("ERROR: could not parse any stretch ids from index.html - aborting to be safe.")
        sys.exit(1)
    print(f"Library has {len(ids)} live stretches.")

    all_photos = []
    for ext in EXTS:
        all_photos += glob.glob(os.path.join(PHOTOS_DIR, f"*.{ext}"))
    all_photos = sorted(set(all_photos))
    print(f"Found {len(all_photos)} photo files in photos/.")

    orphans, wrong, keep = [], [], []
    wrong_set = set(WRONG_PHOTO_IDS)
    for p in all_photos:
        pid = photo_id(p)
        if pid not in ids:
            orphans.append(p)          # stretch no longer exists
        elif pid in wrong_set:
            wrong.append(p)            # flagged wrong photo
        else:
            keep.append(p)

    # wrong ids that have no photo on disk (nothing to delete, but worth noting)
    on_disk_ids = {photo_id(p) for p in all_photos}
    wrong_missing = sorted(i for i in wrong_set if i not in on_disk_ids)

    lines = []
    lines.append("LIMBER PHOTO CLEANUP REPORT")
    lines.append("=" * 32)
    lines.append(f"mode: {'DRY RUN (nothing deleted)' if DRY_RUN else 'LIVE (files deleted)'}")
    lines.append(f"live stretches: {len(ids)}")
    lines.append(f"photos on disk: {len(all_photos)}")
    lines.append("")
    lines.append(f"ORPHAN photos (removed exercises) -> delete: {len(orphans)}")
    for p in orphans:
        lines.append(f"   - {os.path.basename(p)}")
    lines.append("")
    lines.append(f"WRONG-flagged photos -> delete (stretch still exists, needs a new photo): {len(wrong)}")
    for p in wrong:
        lines.append(f"   - {os.path.basename(p)}")
    lines.append("")
    if wrong_missing:
        lines.append(f"WRONG-flagged but no photo on disk (already missing, nothing to delete): {len(wrong_missing)}")
        for i in wrong_missing:
            lines.append(f"   - {i}")
        lines.append("")
    lines.append(f"KEEPING: {len(keep)} photos")
    lines.append("")
    lines.append(f"TOTAL to delete: {len(orphans) + len(wrong)}")

    report = "\n".join(lines)
    print(report)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(report + "\n")

    if DRY_RUN:
        print("\nDRY RUN - no files were deleted. Review cleanup-report.txt.")
        return

    deleted = 0
    for p in orphans + wrong:
        try:
            os.remove(p)
            deleted += 1
        except OSError as e:
            print(f"   ! could not delete {p}: {e}")
    print(f"\nDeleted {deleted} files. See cleanup-report.txt.")


if __name__ == "__main__":
    main()
