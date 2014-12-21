# IRC Point Bot

A simple bot to keep score on IRC.

## Usage

### Simple

Run `python point_bot.py <nick> <channel> <record>` with a Freenode channel and a path to a file to save the points on disk:

    python point_bot.py point_bot "#test" record.yml

### .env

Create a `.env` in the same directory with the nick, channel, and record parameters:

    NICK=point_bot
    CHANNEL=#test
    RECORD=record.yml

Then run without parameters

    python point_bot.py

## Requirements

- pyyaml
- python-dotenv
- irc
