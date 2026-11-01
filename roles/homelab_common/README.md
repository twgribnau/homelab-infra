# homelab_common

What the stacks share: the Docker network they talk over and the data folders in the
[TRaSH Guides](https://trash-guides.info/File-and-Folder-Structure/) layout, so imports are
hardlinks instead of copies.

- **Runs:** always (tag `always`: the other roles need it).
- **Settings:** the paths and network in `inventory/group_vars/homelab/main.yml`.
