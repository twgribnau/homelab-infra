# books_stack

[Calibre-Web Automated](https://github.com/crocodilestick/Calibre-Web-Automated): your ebook
library in the browser and synced to a Kobo. Books in `books-ingest` are imported into it.

- **Runs:** with `homelab_books: true` (the default). Tag: `books`.
- **Settings:** `defaults/main.yml`: the image version.
- **Note:** on every network as plain http (a Kobo can't run Tailscale), and over Tailscale HTTPS
  on `:8443`. The login, Kobo sync and users are set by `app_config`.
