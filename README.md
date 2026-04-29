# O2 (UK) for Home Assistant

An unofficial Home Assistant integration that scrapes the My O2 (UK)
self-service portal at <https://my.o2.co.uk> and exposes your account
information as sensors.

## Sensors

| Sensor                | Description                                 |
| --------------------- | ------------------------------------------- |
| Data remaining        | Mobile data remaining this billing period   |
| Data used             | Mobile data used this billing period        |
| Data allowance        | Total mobile data allowance                 |
| Minutes remaining     | Voice minutes remaining                     |
| Minutes used          | Voice minutes used                          |
| Texts remaining       | SMS messages remaining                      |
| Texts used            | SMS messages used                           |
| Allowance reset       | Date the current allowance resets           |
| Latest bill amount    | Most recent bill total (Pay Monthly only)   |
| Latest bill date      | Date of the most recent bill                |

If your tariff includes an unlimited allowance, the corresponding
"remaining" sensor reports `unlimited`.

## Installation

### HACS

1. Add this repository as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories) in HACS.
2. Install **O2 (UK)** from HACS.
3. Restart Home Assistant.

### Manual

1. Copy `custom_components/o2uk` into your Home Assistant `config/custom_components` directory.
2. Restart Home Assistant.

## Configuration

Add the integration from **Settings → Devices & Services → Add Integration**
and enter your My O2 username and password. Polling defaults to every 30
minutes; this can be changed in the integration's options.

## Caveats

- The My O2 portal does not expose a public API, so this integration
  scrapes endpoints used by the website. Those endpoints can change at
  any time.
- Tested only with a single Pay Monthly account. Multi-line accounts and
  Virgin Media O2 (VMO2) accounts are not supported.
- Storing your password is required because the portal uses a regular
  form login. Consider using a Home Assistant secret.

## Development

```sh
pip install -e .[dev]
pytest
ruff check .
```
