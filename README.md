# O2 (UK) for Home Assistant

An unofficial Home Assistant integration that polls the My O2 (UK)
self-service dashboard and exposes your account state — data, minutes,
texts, spend cap, monthly charge — as sensors.

## How it works

O2 has migrated the My O2 portal to a PingOne DaVinci login that
requires a JavaScript-generated device-fingerprint payload. There is no
practical way to drive that login from pure Python, and the obvious
fallback (driving a headless browser inside Home Assistant) doesn't
work on Home Assistant OS, whose Python environment is musl-based.

So this integration takes a different approach: **you log in once in
your normal browser and paste the resulting cookies into the
integration's config**. From then on the integration polls
`https://www.o2.co.uk/ecare/home` with those cookies and parses the
inline data the dashboard returns.

When the cookies expire, Home Assistant raises a re-auth notification,
and you paste a fresh `Cookie` header.

## Sensors

| Sensor             | Description                                  |
| ------------------ | -------------------------------------------- |
| Data remaining     | Mobile data remaining this billing period    |
| Data used          | Mobile data used this billing period         |
| Data allowance     | Total mobile data allowance                  |
| Minutes used       | Voice minutes used                           |
| Minutes remaining  | Voice minutes remaining (if not unlimited)   |
| Texts used         | SMS messages used                            |
| Texts remaining    | SMS messages remaining (if not unlimited)   |
| Allowance reset    | Date the current allowance resets            |
| Spend cap          | Pay Monthly spend cap (£)                    |
| Monthly charge     | Headline monthly tariff charge (£, incl. VAT)|

If a tariff allowance is unlimited, the corresponding "remaining"
sensor reports as unavailable rather than `-1`.

## Installation

### HACS

1. Add this repository as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories) in HACS.
2. Install **O2 (UK)** from HACS.
3. Restart Home Assistant.

### Manual

1. Copy `custom_components/o2uk` into your Home Assistant
   `config/custom_components` directory.
2. Restart Home Assistant.

## Configuration

### 1. Sign in to My O2 in your browser

Open <https://www.o2.co.uk/ecare/home> and sign in until you see your
account dashboard.

### 2. Copy the `Cookie` header

In Chrome, Firefox, or Safari:

1. Open DevTools → **Network** tab. Tick **Preserve log**.
2. Reload the dashboard page.
3. Click the request to `ecare/home` (the one that returns HTML, not
   the static assets).
4. Open the **Headers** sub-tab and find **Request Headers** →
   **`Cookie:`**.
5. Right-click the value → Copy. (Firefox: "Copy value". Chrome: select
   the whole value, ⌘/Ctrl-C.)

### 3. Add the integration

1. **Settings → Devices & Services → Add Integration → O2 (UK)**.
2. Paste the cookie value into the **Cookie header** field.
3. Submit.

The integration validates the cookies by fetching the dashboard once;
if it works you'll see the sensors appear immediately.

### 4. When cookies expire

You'll see a "Re-authentication required" notice in Home Assistant.
Repeat steps 1 and 2 above and paste the fresh value into the re-auth
form, or open the integration's Options to paste new cookies any time.

In practice O2 sessions last days to a couple of weeks.

## Caveats

- The dashboard layout is undocumented; if O2 changes the page
  structure the parser may need updating.
- Tested only with a single Pay Monthly account. Multi-line accounts
  and Virgin Media O2 (VMO2) accounts are not supported.

## Development

```sh
pip install -e .[dev]
pytest
ruff check .
```

The parser tests run against a sanitized capture of a real ecare
dashboard response (`tests/fixtures/ecare_home.html.gz`).
