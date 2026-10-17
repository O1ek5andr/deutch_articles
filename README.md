# German Articles Telegram bot

## Run locally

Install dependencies and set `TELEGRAM_TOKEN` in a local `.env` file (see
[.env.example](.env.example)):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python deutch_articles.py
```

## Deploy both bots to one Ubuntu VM

This bot uses Telegram long polling, so the VM needs outbound internet access
but no public web server or inbound application port. The included
[systemd unit](deploy/deutch-articles.service) starts it on boot and restarts it
if it exits.

1. Install Python, venv support, and Git:

   ```sh
   sudo apt update
   sudo apt install -y git python3 python3-venv
   ```

2. Create a dedicated service account and application directory. Run the
   `useradd` command only if you have not already created this account for the
   other bot:

   ```sh
   sudo useradd --system --create-home --home-dir /opt/bots --shell /usr/sbin/nologin botuser
   sudo install -d -o botuser -g botuser /opt/bots/deutch_articles
   sudo -u botuser git clone https://github.com/O1ek5andr/deutch_articles.git /opt/bots/deutch_articles
   ```

3. Create a private environment file and put the token from BotFather in it:

   ```sh
   sudo install -m 600 /dev/null /etc/deutch-articles.env
   sudo nano /etc/deutch-articles.env
   ```

   Add `TELEGRAM_TOKEN=your-real-token`. Do not commit this file or copy a
   `.env` file into the repository.

4. Create the virtual environment, install dependencies, and install the
   service:

   ```sh
   sudo -u botuser python3 -m venv /opt/bots/deutch_articles/.venv
   sudo -u botuser /opt/bots/deutch_articles/.venv/bin/pip install -r /opt/bots/deutch_articles/requirements.txt
   sudo cp /opt/bots/deutch_articles/deploy/deutch-articles.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now deutch-articles
   ```

5. Check status and logs:

   ```sh
   sudo systemctl status deutch-articles
   sudo journalctl -u deutch-articles -f
   ```

For the PowerPoint bot, repeat these steps using its service instructions in
that repository. Each bot needs its own Telegram token and service; don't run
two polling processes with the same token. The German bot writes `results.json`
in its application directory, which is kept on the VM across service restarts.
