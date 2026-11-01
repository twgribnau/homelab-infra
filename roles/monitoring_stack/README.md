# monitoring_stack

Prometheus, node-exporter and cAdvisor (server and container metrics), Grafana with one
dashboard and alerts, and [Homepage](https://gethomepage.dev), the start page with every app.

- **Runs:** with `homelab_monitoring` or `homelab_homepage` (both on by default); each part
  only when its switch is on. Tag: `monitoring`.
- **Settings:** `defaults/main.yml`: the image versions and how long Prometheus keeps data.
  Homepage's look: `files/homepage/`; its apps and widgets come from `app_config`.
