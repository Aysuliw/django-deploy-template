# Server checklist

A fresh Ubuntu server, before the app goes on it. Each item is here because skipping it
has gone wrong for someone, usually through a cryptominer arriving via a weak SSH password
or an exposed database.

## Access

- [ ] Log in with SSH keys only: `PasswordAuthentication no`, `PermitRootLogin prohibit-password`
      (or `no`, with a sudo user) in `/etc/ssh/sshd_config`, then `systemctl reload ssh`.
- [ ] `fail2ban` for SSH.
- [ ] Firewall: `ufw default deny incoming`, allow only `22`, `80`, `443`, then `ufw enable`.
      Note that Docker writes its own iptables rules and **bypasses ufw for published ports**.
      That's why `docker-compose.yml` publishes nginx only, never PostgreSQL.

## Updates

- [ ] `unattended-upgrades` for security updates.
- [ ] Pin image versions (`postgres:16`, `nginx:1.27-alpine`) and update them on purpose.

## Secrets

- [ ] `.env` and `/etc/app-backup.env` are `chmod 600`, owned by the deploy user, never in git.
- [ ] The age **private** key for backups lives off the server.
- [ ] A different, long `SECRET_KEY` and database password per environment.

## Watching

- [ ] An uptime monitor on `https://example.com/healthz/` (it returns 503 if the database is down).
- [ ] Errors go to Sentry and/or Telegram (`SENTRY_DSN`, `TELEGRAM_*` in `.env`).
- [ ] Backups alert on failure, and `deploy/restore-check.sh` runs at least monthly.

## If the server is already slow and you don't know why

Signs of a cryptominer: a process at 100% CPU with a random or system-like name, often running
from `/tmp`, `/dev/shm` or `/var/tmp`.

```sh
top -o %CPU                                  # what is eating the CPU
ls -la /proc/<pid>/exe                       # where the binary really lives
crontab -l; ls /etc/cron.*; systemctl list-timers   # how it comes back after a kill
cat ~/.ssh/authorized_keys /root/.ssh/authorized_keys   # keys you didn't add
ss -tunap | grep ESTAB                       # connections to mining pools
```

Kill the process, remove the binary **and** whatever restarts it (cron, systemd unit, SSH key),
then close the way in: usually a password login, an exposed database port or an outdated
service. Then rotate every secret that was on that server.
