# Ahmad El Yakubu

[linkedin](https://www.linkedin.com/in/ahmaedy/) · [x](https://x.com/ElyakubuAhmad) · [email](mailto:ahmadelyakubu@gmail.com)

## about

> Electrical Engineering student at ABU, Zaria, Nigeria.
> Confused by hardware and software in equal measure.

My first project was a chatbot I built at 11. It was bad. I've been
building ever since, learning mostly by brute-force trial and error, and
later through Turing Award winner Leslie Lamport's line: *"Coding is to
programming what typing is to writing."* The syntax is the easy part. The
logic is the craft.

Right now that's **[Zars](https://github.com/Ahmaaedy/zars)**, an
on-device local assistant with a decision-model layer. It's built to be
faster than the alternatives by deciding instead of guessing.

Off the keyboard, or at least adjacent to it:
- **Arch Linux, btw.** Deep in the ricing scene. If my desktop doesn't
  look intentional, something's wrong.
- **Homelab:** a server running my research scripts and storage. My own
  corner of the internet, and I'm the only one on call when it breaks.
- **Rubik's cube PB: 1:43.** Not fast, still proud.
- **Chess:** played badly, with great confidence.

My code isn't distributed-systems-proof yet. My ego is.

## stack

`python` `react` `html` `css` `javascript` `linux` `rust (learning)`

## projects

**[Damha](https://github.com/Ahmaaedy/damha)** · `python, telethon, ctrader, metatrader5`
Trading bot that reads Telegram and forum chatter, pulls out SL/TP levels,
and has AI vet each call before firing a market order. Variants add
MetaTrader5 support, desktop toasts, and email alerts.

**[Pharmx](https://github.com/Ahmaaedy/pharmx)** · `fastapi, react, tailwind`
Medication safety checker. Give it a drug list and labs, and it returns one
severity-ranked report of interactions and renal-dosing risks.

**[Campus Guardian AI](https://github.com/Ahmaaedy/cga)** · `react, express, capacitor, gemma`
Safety app for ABU: complaint submission, one-tap emergency SMS, and an
on-device LLM that answers university questions without needing a server.

**[StreamCBT](https://github.com/Ahmaaedy/streamcbt)** · `html, css, javascript`
Free CBT prep for university students: timed tests, instant scored review,
course handbooks, and a video lecture library. A static site, no build step.

**[video-editing-agent](https://github.com/Ahmaaedy/video-editing-agent)** · `python, streamlit, whisper, gpt-4`
Upload a video and a script, and it transcribes with word-level timestamps,
picks the best takes, and cuts stutters and repeats.

## stats

![stats](stats.svg)
![streak](streak.svg)
![languages](langs.svg)
![year](year.svg)

## about this page

Every graphic here is generated, not embedded from anyone else's server. A
scheduled GitHub Action runs `scripts/generate.py` once a day, pulls data
from the GitHub GraphQL API, and commits only what changed. They animate
with SMIL inside the SVG, because GitHub strips scripts from READMEs.

Language totals cover public repositories only. `year.svg` draws one
character per day, `.` `:` `+` `#` `@`, quiet to loud.
