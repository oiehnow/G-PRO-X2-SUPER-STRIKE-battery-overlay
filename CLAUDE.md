# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

This repository currently contains only a planning document (`project plan.txt`, in Korean). **No code, build system, or tests exist yet.** The sections below describe the intended project so implementation can start correctly. Update this file once a stack is chosen and scaffolding lands.

## What we're building

A small Windows desktop **overlay** that displays the battery level and estimated remaining runtime of a **Logitech PRO X2 Superstrike** wireless mouse. The overlay must be toggleable on/off via a hotkey and stay small/unobtrusive. G HUB already shows battery, but the goal is a lightweight always-available overlay plus a "time remaining" estimate that G HUB does not provide.

## Critical architecture decision (read before coding)

Do **not** try to talk to the mouse directly over raw HID. The PRO X2 / Superstrike line uses Logitech's newer **"Centurion" protocol**, not standard HID++ 2.0, so common Python/hidapi battery snippets will not work and reverse-engineering it is a large effort.

Instead, the design is **scout-out, build-the-front-end**:

- **Backend (do not build):** [`LGSTrayEx`](https://github.com/) — an open-source C#/GPL-3.0 Windows tray app that already implements the Centurion protocol and lists `(Lightspeed) G Pro X 2 Mouse` as supported. It reads the battery % and serves it over a **local HTTP XML endpoint** (also MQTT). The port and XML schema are configured in `appsettings.toml` (http server section) of an installed LGSTrayEx — confirm the actual port/format there rather than hardcoding assumptions.
- **Frontend (what we build):** poll the LGSTrayEx local HTTP/XML endpoint periodically, parse battery % (and `is_online`), compute remaining time, and render a small toggleable overlay window.

So the hard part (mouse communication) is delegated; our work is the overlay UI, hotkey toggle, polling/parsing, and time estimation.

## "Remaining time" must be computed, not read

The mouse reports only % (or voltage), never hours remaining. Estimate it by logging `(timestamp, battery%)` samples, deriving the discharge rate (%/hour), and computing `remaining = current% / discharge_rate`. Before enough samples accumulate, fall back to the spec baseline (~60–90 hours of battery life).

## Overlay constraint (decide up front)

A normal topmost window draws over **borderless** fullscreen games but **not** true **exclusive fullscreen**. If the overlay must appear over FPS games, require borderless mode or target a second monitor. Decide this before building the overlay to avoid wasted effort.
