# backup

Every night the app data and the ebook library to the cloud: [restic](https://restic.net),
encrypted with `vault_backup_password`, through [rclone](https://rclone.org) to Google Drive,
OneDrive, Backblaze B2 or another cloud. Not the movies and series: Radarr and Sonarr get them again.

- **Runs:** when `homelab_backup_remote` is set (`config/settings.yml`), with the rclone remote in
  `vault_rclone_config` (`config/vault.yml`). Tag: `backup`. The main README, Offsite backup, has
  the steps for Google Drive and how to restore.
- **Settings:** `defaults/main.yml`: the time, how many backups to keep, the copy's folder.
- **Note:** the apps stop only while their data is copied to `/backup/staging` (seconds), so the
  copy is consistent; the upload runs from that copy. It never runs during an automatic deploy
  (`homelab_lock`). Log: `journalctl -u homelab-backup`.
