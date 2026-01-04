# Camp Chef – Home Assistant Custom Integration
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Bluetooth](https://img.shields.io/badge/Integration-Bluetooth-blue.svg)](https://www.home-assistant.io/integrations/bluetooth/)
[![ESPHome Bluetooth Proxy](https://img.shields.io/badge/ESPHome-Bluetooth%20Proxy-blue.svg)](https://esphome.io/components/bluetooth_proxy.html)
[![License](https://img.shields.io/github/license/doggkruse/ha-campchef.svg)](LICENSE)

Local Bluetooth Low Energy (BLE) integration for **Camp Chef–family pellet grills** (Camp Chef, Cabela’s, Kingsford) in Home Assistant, powered by the `pycampchef` library.

This integration provides **cloud-free monitoring and control** directly from Home Assistant.

---

## Features

- **Local BLE control** (no cloud dependency)
- **Config flow** with Bluetooth discovery
- Automatic grill capability detection
- Hybrid **push (notifications) + polling** update model

### Entities

#### Climate
- Grill chamber temperature (current & target)

#### Sensors
- Grill mode
- Pellet level
- Probe temperatures
- Wi-Fi RSSI
- Wi-Fi SSID
- OTA update state
- OTA update progress
- Fault status
- Transitioning state
- Fan status

#### Binary sensors
- Wi-Fi connectivity

> Diagnostic and high-churn entities are **disabled by default** and can be enabled individually from the entity registry.

---

## Supported devices

This integration targets pellet grills that implement the **Camp Chef BLE protocol**, including compatible models sold under:

- Camp Chef
- Cabela’s
- Kingsford

Exact feature availability depends on the grill’s firmware and reported capabilities.

---

## Installation

### Option 1: HACS (recommended)

1. Add this repository as a **custom repository** in HACS.
2. Install **Camp Chef** from HACS.
3. Restart Home Assistant.

### Option 2: Manual installation

1. Copy the contents of this repository to: `config/custom_components/camp_chef/`

2. Restart Home Assistant.

---

## Setup

1. Go to **Settings → Devices & Services**
2. Click **Add Integration**
3. Select **Camp Chef**
4. Choose a discovered Bluetooth device

Bluetooth discovery will automatically prompt setup when supported grills are detected.

---

## Bluetooth & pairing notes

- Uses Home Assistant’s built-in Bluetooth stack
- No custom pairing UI is provided
- Grills require bonding before encrypted BLE traffic will succeed.  On some bluetooth stacks such as esphome bluetooth proxy this will just work.

If pairing is required:
- Pair the grill **once** at the OS level (e.g. via `bluetoothctl` on HAOS)
- The stored bond is reused automatically by Home Assistant

### ESPHome Bluetooth Proxy

When using the
[ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy.html),
some grill models may not support BLE notification subscriptions through the proxy.

In this case, the integration will automatically operate in **polling mode** to
retrieve state updates. No user configuration is required.

---

## Update model

- When BLE notifications are available, state updates are **pushed in near-real-time**
- A periodic polling backstop ensures state recovery if notifications stop
- The integration avoids excessive polling to reduce BLE load

---

## Disclaimer

This project is **not affiliated with or endorsed by Camp Chef**, Cabela’s, Kingsford, or related brands.

---

## License

This project is licensed under the **Apache License, Version 2.0**.

Apache-2.0 is compatible with inclusion in the Home Assistant Core repository and allows redistribution, modification, and contribution under the same terms.

See the `LICENSE` file for full license text.