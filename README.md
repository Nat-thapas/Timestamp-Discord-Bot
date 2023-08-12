# Timestamp Discord Bot
---
## What is this for?
Have you ever wanted to create a Discord timestamp such as `<t:1691829000:f>` which will be rendered as `12 August 2023 15:30` on Discord? This bot help you easily achive that.
## Usage
### Manual mode
> Command: `/timestamp manual`

In this mode, the user have to specify day, month, year, hour, and minute separately in different slash command arguments. There are also 2 optional which is second and timezone, the supported timezone format are ±hh:mm or ±hh (leading zero in the hours part can be omitted). By default the timezone used is UTC. No DST support as of now.

### Automatic mode
> Command: `/timestamp automatic`

In this mode, the user just have to enter a natural language time, such as `12th August 16:15` and the bot will parse that automatically. This mode also support the timezone argument like manual mode. By default the timezone used is UTC. No DST support as of now.

### Response
The bot's response will be ephemeral, which mean that only the person who used the slash command can see it. In the response will be both the timestamp embed that you can copy to your own message, and the preview of what that'll look like when rendered.

## Installation / Hosting
The installation and hosting process is like any other python code, install the required dependency (for now just look at the code as requirements.txt doesn't exist yet) and just run it with `python3 main.py`. The only extra thing you have to do is create a `.env` file in the same folder as the `main.py` and put your bot's token in there, for example `TOKEN = QWERTY1234`
