# O2 (UK) for Home Assistant

An unofficial Home Assistant integration that surfaces your My O2 (UK)
account state — data, minutes, texts, spend cap, monthly charge — as
sensors.

## How it works

O2 has migrated the My O2 portal to a PingOne DaVinci login that
requires a JavaScript-generated device-fingerprint payload. There is no
practical way to drive that login from pure Python, so this integration
performs the login with **headless Chromium via Playwright** the first
time, persists the resulting session cookies, and then polls the
`https://www.o2.co.uk/ecare/home` dashboard with plain HTTP. The
dashboard is server-rendered, with all account data embedded inline as
React Server Components, so a single GET is enough to refresh every
sensor.

When the persisted session expires (the dashboard responds with a
sign-in page) the integration silently re-runs the Playwright login.

## Sensors

| Sensor             | Description                                  |
| ------------------ | -------------------------------------------- |
| Data remaining     | Mobile data remaining this billing period    |
| Data used          | Mobile data used this billing period         |
| Data allowance     | Total mobile data allowance                  |
| Minutes used       | Voice minutes used                           |
| Minutes remaining  | Voice minutes remaining (if not unlimited)   |
| Texts used         | SMS messages used                            |
| Texts remaining    | SMS messages remaining (if not unlimited)    |
| Allowance reset    | Date the current allowance resets            |
| Spend cap          | Pay Monthly spend cap (£)                    |
| Monthly charge     | Headline monthly tariff charge (£, incl. VAT)|

If your tariff includes an unlimited allowance, the corresponding
"remaining" sensor reports as unavailable rather than a number.

## Installation

### Prerequisites — Playwright + Chromium

The integration depends on `playwright`, which is declared in the
manifest. After installing the integration, Home Assistant will install
the Python package automatically. You also need to install the Chromium
binary it drives once, by running this *inside the Home Assistant
environment* (e.g. inside the `homeassistant` container or venv):

```sh
python -m playwright install chromium
```

If you're on Home Assistant OS or the official container, this step
needs the operating system's Playwright dependencies — see
[the Playwright docs](https://playwright.dev/python/docs/intro) for the
list. On a standard Linux install, `playwright install --with-deps
chromium` handles it.

### HACS

1. Add this repository as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories) in HACS.
2. Install **O2 (UK)** from HACS.
3. Restart Home Assistant.
4. Run `python -m playwright install chromium` in the HA environment.

### Manual

1. Copy `custom_components/o2uk` into your Home Assistant `config/custom_components` directory.
2. Restart Home Assistant.
3. Run `python -m playwright install chromium` in the HA environment.

## Configuration

Add the integration from **Settings → Devices & Services → Add
Integration**. Enter your My O2 username (email) and password. The
first setup will take ~30s while Playwright performs the initial
login. Polling defaults to every 30 minutes; this can be changed in the
integration's options.

## Caveats

- The My O2 portal is an undocumented surface. If O2 changes the page
  structure, the parser may need updating.
- Tested only with a single Pay Monthly account. Multi-line accounts
  and Virgin Media O2 (VMO2) accounts are not supported.
- Storing your password is unavoidable — re-authentication is
  fully automated and happens whenever the session expires.
- The integration runs a real Chromium browser briefly during initial
  setup and on session expiry. This is not lightweight; expect ~150 MB
  RAM during those windows.

## Development

```sh
pip install -e .[dev]
playwright install chromium
pytest
ruff check .
```

The parser tests run against a sanitized capture of a real ecare
dashboard response (`tests/fixtures/ecare_home.html.gz`).
