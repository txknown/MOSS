# Backups, recovery, and upgrades

MOSS stores data in ordinary local files. A memory snapshot contains nodes,
materials, system settings, and action logs, plus `SNAPSHOT.txt` and the installed
`version.txt`. It does not include application code or the Python environment.

## Create a backup

1. Finish pending edits and pause other agents or terminal sessions writing to
   this workspace.
2. Open **Snapshots**, enter a descriptive name, and create the snapshot.
3. Download it or copy the ZIP from `snapshots/` to your backup location.

Snapshot names must be unique; creating a snapshot does not overwrite an older
archive. The snapshot action is recorded after the archive is written, so the
archive's action log does not contain its own creation entry.

You can also stop MOSS and copy the complete `memory/` directory. To preserve
custom code and custom palette/style definitions, back up the source separately.
Keep the code version associated with the backup for recovery.

## Restore a snapshot

v1.1.0 has no in-app restore button. Restore manually:

1. Stop the web server with **Ctrl+C**, close the terminal interface, and stop
   agents from writing to this installation.
2. Extract your snapshot ZIP into a separate temporary folder. Confirm it has
   a top-level `memory/` directory and inspect `SNAPSHOT.txt` for its version.
3. Move the installation's current `memory/` directory to a separate dated
   backup location. Keep it until you have verified the recovery.
4. Copy the extracted `memory/` directory into the installation, beside `core/`,
   `web/`, and `start_web.py`. Replace the whole directory rather than merging
   old and restored contents: merging can retain nodes that were not in the backup.
5. Start MOSS and check Home, important notes, materials, and UI settings.

Do not copy the snapshot's `version.txt` over the application's version file.
It describes the source version of the backup; replacing it does not restore
that code. Use the same or a compatible newer MOSS release to read the data.
If recovery is wrong, stop MOSS and restore the directory saved in step 3.

## Upgrade from v1.0.0

v1.1.0 reads existing v1.0.0 nodes without a bulk migration. New attributes and
presentation settings use defaults until explicitly changed. Existing titles,
text, dates, child order, log-entry answers, and materials remain intact.

1. Stop MOSS and make a backup of `memory/` and any code you have customized.
2. If using Git, inspect `git status`. Reconcile your code edits before pulling
   the public update; do not discard local changes to force an upgrade.
3. Update the source to v1.1.0. Keep `memory/` and `snapshots/` in place. If using
   a downloaded source copy, copy your backed-up memory into that installation
   before its first launch.
4. In the updated installation, reinstall the recorded dependencies:

   ```sh
   .venv/bin/python -m pip install -r requirements.txt
   ```

5. Launch `.venv/bin/python start_web.py`, reload any existing browser tab, and
   check your workspace. `/` honors startup preferences; `/node/home` opens Home
   directly. Windows uses `.venv\Scripts\python.exe` for these commands.

The public launcher keeps port **8766**. An occupied port is an error, even when
another MOSS instance responds there, to avoid silently opening a different
workspace. Stop the process using the port before launching this installation.

## Sharing source

Git ignores memory, snapshots, environments, and caches. A ZIP or folder copy
includes files regardless of `.gitignore`, so inspect what you share. Preferences
can contain personal node IDs and labels; action logs and snapshots can contain
private content too. None belongs in a public source release.
