# Demented Discord Bot

A feature-rich Discord bot with various commands and event handling capabilities including random insults, jokes, games, moderation tools, and voice channel interaction. Built with discord.py 2.x.

## Installation

If you just want to use the bot in your server, you can install it using this link:
- [Add Bot to Your Server](https://discord.com/oauth2/authorize?client_id=1314688956989964388)

## Features

- **Modern Slash Commands**: Using discord.py 2.x app_commands
- **Fun Commands**: Jokes, insults, games, and more entertainment
- **Moderation Tools**: Ban, kick, mute, temp-ban, and message management
- **Voice Channel Interaction**: Play sound effects in voice channels
- **Optimized API Integration**: With HTTP session management and caching
- **Sentiment Analysis**: Smart responses based on message sentiment
- **Interactive Commands**: Games, polls, and user interaction
- **Performance Monitoring**: Command timing and usage tracking

## Setup & Installation

For detailed installation instructions, please see [INSTALL.md](INSTALL.md).

Quick start:

1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies:

```bash
# Install dependencies
pip install -r requirements.txt
```

4. Create a `.env` file with your bot token:

```
BOT_TOKEN=your_discord_bot_token_here
```

5. Run the bot:

```bash
python discord_bot.py
```

> **Note:** Voice features require FFmpeg to be installed on your system.

## Project Structure

```
Demented-Discord-Bot/
├── discord_bot.py         # Main bot entry point
├── update_commands.py     # Script to sync slash commands
├── cogs/                  # Command modules
│   ├── api.py             # API integration commands
│   ├── minimal.py         # Basic commands
│   ├── slash.py           # Slash commands
│   └── ...                # Other command modules
├── data/                  # Data files and utilities
│   ├── config.json        # Bot configuration
│   ├── helper_functions.py # Shared utility functions
│   ├── keep_alive.py      # Web server for uptime
│   ├── session_manager.py # HTTP session management
│   └── ...                # Game data files
└── bot_sounds/            # Sound files for voice commands
```

## Configuration

You can configure the bot by editing the `data/config.json` file, which contains settings for:

- Command prefix
- Activity statuses
- Feature toggles
- API timeouts
- Cache durations

## Commands

### General
- `/ping` - Check bot latency
- `/uptime` - Check bot uptime
- `/server-stats` - Get server information
- `/user-info` - Get user information

### Fun
- `/joke` - Get a random joke
- `/8ball` - Ask the magic 8-ball
- `/bored` - Get a random activity suggestion
- `/mock` - Convert text to alternating case
- `/reverse` - Reverse text
- `/clapify` - Add clap emojis between words

### Moderation
- `/ban` - Ban a user
- `/tempban` - Temporarily ban a user
- `/kick` - Kick a user
- `/mute` - Timeout a user
- `/unmute` - Remove timeout
- `/clear` - Clear messages

### Games
- `/truth` - Get a truth question
- `/dare` - Get a dare
- `/never` - Get a "never have I ever" question
- `/thisorthat` - This or that game
- `/wouldyourather` - Would you rather questions

### Voice
- Mention the bot with "join" to play random sound effects in your voice channel

## Credits

- NLTK chat events - Credit to [YungSchmeg](https://github.com/JCoombs224/discord-chat-bot-nltk)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
