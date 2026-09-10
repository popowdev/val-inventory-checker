# Valinven

See your Valorant inventory and what it is worth — **without launching the game**.

You sign in to your Riot account in the official Riot window, and the tool reads your
skins. Neither Valorant nor Riot Client has to be running.

## Getting started

Double-click **`START.bat`**, then press:

- **1** — opens the interface in your browser. Click **"Sign in to Riot"**, sign in, and
  your inventory appears.
- **2** — exports the inventory to JSON and CSV in the `exports/` folder.
- **3** — signs out and forgets the saved Riot session.

The launcher installs its dependencies on first run. You need Windows 10 or 11 and
Python 3.

If Riot Client happens to be running, the tool uses it and asks for nothing.

## What it does with your account

- The sign-in window is the **official Riot page**. The tool never sees your password —
  only the token Riot hands back.
- Tokens are kept in memory and sent to Riot APIs and nowhere else.
- The catalog and images come from [valorant-api.com](https://valorant-api.com). Public
  skin pages are fetched without any account id or token.
- Nothing is written to disk apart from your own exports.
- The tool is **read-only**. It cannot buy, equip or change anything.

## About the prices

Prices in euros are an estimate, prorated from the nearest VP tier. The total is a catalog
value — not what you spent, and not a resale value. Battle passes, contracts and skins with
no individual price are excluded. Full details are under "Privacy & valuation method" in
the interface.

## Development

```
py -3 -m pip install -r requirements-dev.txt
py -3 -m pytest tests/ -q
```

## Credits

Built by **Popow** and **Hadori**.

Powered by [Surfsmart.fr](https://surfsmart.fr)

## Disclaimer

Valinven is not endorsed by Riot Games and does not reflect the views or opinions of Riot
Games or anyone officially involved in producing or managing Riot Games properties.
Valorant and Riot Games are trademarks or registered trademarks of Riot Games, Inc.

Use it on your own account, at your own risk.
