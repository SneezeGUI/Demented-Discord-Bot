# Demented Discord Bot

Welcome to the home of Demented, a powerful, multi-faceted Discord bot designed to bring a unique blend of chaos, entertainment, and robust administration to your server. Powered by a witty and unhinged AI, Demented is more than just a utility—it's a personality.

This bot integrates cutting-edge features like a secure OAuth2 verification system, a conversational AI with long-term memory, and a full suite of moderation and entertainment commands, all built on a modern `discord.py 2.x` framework.

## Key Features

*   🤖 **Conversational AI**: Engage in dynamic, context-aware conversations. The bot remembers facts about users, has a fluctuating mood, and can start conversations on its own when it gets bored.
*   🔒 **Secure Member Verification**: A professional-grade OAuth2 system that requires new members to authorize through Discord, ensuring server safety and integrity. It automatically manages roles and handles users who deauthorize the bot.
*   🛡️ **Comprehensive Moderation**: A full suite of slash commands for server management, including `/kick`, `/ban`, `/unban`, `/mute` (timeout), and `/clear`.
*   🎉 **Entertainment & Games**: A wide array of fun commands, from interactive games like `Truth or Dare` and `Would You Rather` to meme generation and simple social interactions like `/slap` and `/hug`.
*   🌐 **API Integrations**: Fetches jokes, memes, and activities from various external APIs, with built-in caching for performance.
*   ⚙️ **Advanced Configuration**: Server owners can configure bot behavior, including setting up verification roles, restricting channels, and enabling/disabling autonomous AI chat.

## Adding Demented to Your Server

To invite the bot to your Discord server, use the official authorization link:

- **Add Demented to Your Server**

## Setup for Server Admins

To get the most out of the bot, especially the verification system, follow these steps:

1.  **Create Roles**: In your server, create two roles: one for verified members (e.g., `@Verified`) and one for unverified members (e.g., `@Unverified`).
2.  **Configure Roles**: Use the `/config verification set-role` command to assign these roles to the bot.
    *   `/config verification set-role type:verified role:@Verified`
    *   `/config verification set-role type:unverified role:@Unverified`
3.  **Deploy Verification Panel**: Go to your designated verification channel and run `/verify setup`. This will post a persistent message with a "Verify Me" button.

Your server is now protected by the secure verification system!

## Command Showcase

Demented uses a mix of modern slash commands (`/`) and traditional prefix commands (`!`).

<details>
<summary>🤖 <strong>AI Commands</strong></summary>

-   `/ask [question]` - Ask the AI a question directly.
-   `/remember [user] [fact]` - (Admin) Teach the AI a fact about a user.
-   `/soul-status [user]` - (Owner) Check the bot's internal mood and its sentiment towards a user.
-   The bot will also respond to mentions, replies, or its name being said in chat.

</details>

<details>
<summary>🛡️ <strong>Moderation Commands</strong></summary>

-   `/clear [amount]` - Clears a specified number of messages (1-100).
-   `/kick [member] [reason]` - Kicks a member from the server.
-   `/ban [member] [reason]` - Bans a member from the server.
-   `/unban [user_id] [reason]` - Unbans a user using their ID.
-   `/mute [member] [duration] [reason]` - Mutes a member for a specified duration in minutes.
-   `/unmute [member] [reason]` - Removes a timeout from a member.

</details>

<details>
<summary>🔒 <strong>Verification Commands</strong></summary>

-   `/verify setup` - (Admin) Posts the verification panel in the current channel.
-   `/verify pull [user_id]` - (Admin) Force-adds a previously authorized user to the server.
-   `/verify pull-all` - (Admin) Attempts to add all users who have ever authorized the bot.

</details>

<details>
<summary>🎉 <strong>Fun & Games Commands</strong></summary>

-   `/8ball [question]` - Ask the magic 8-ball a question.
-   `/roll [max_number]` - Rolls a random number.
-   `/hug`, `/pat`, `/slap-slash` - Interact with other users.
-   `/reverse [text]` - Reverses the given text.
-   `!truth` / `!dare` / `!never` - Get a question for popular party games.
-   `!thisorthat` / `!wouldyourather` / `!button` - Interactive polling games.

</details>

<details>
<summary>🌐 <strong>API & Utility Commands</strong></summary>

-   `/user-info [user]` - Shows detailed information about a user.
-   `/joke-api [category]` - Get a joke from a specific category.
-   `/bored [participants]` - Get a random activity suggestion.
-   `!reddit [subreddit]` - Fetches a hot image post from any subreddit.
-   `!meme` / `!dank` - Quick shortcuts for popular meme subreddits.

</details>

## For Developers

Interested in running your own instance or contributing to the project?

### Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/SneezeGUI/Demented-Discord-Bot.git](https://github.com/SneezeGUI/Demented-Discord-Bot.git)
    cd Demented-Discord-Bot
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    The project uses `setuptools` for dependency management. Install all required packages, including development tools, with:
    ```bash
    pip install -e ".[dev]"
    ```

4.  **Configure Environment:**
    Create a `.env` file in the root directory and fill it with your credentials. See `.env.example` for the required fields.
    ```toml
    # .env
    BOT_TOKEN="your_discord_bot_token"
    CREATOR_ID="your_discord_user_id"
    GEMINI_API_KEY="your_google_ai_api_key"

    # For Verification System
    CLIENT_ID="your_bot_client_id"
    CLIENT_SECRET="your_bot_client_secret"
    CLIENT_PUBLIC_KEY="your_bot_public_key"
    REDIRECT_URI="http://localhost:8080/callback"
    ```

5.  **Run the bot:**
    ```bash
    python discord_bot.py
    ```
    > **Note:** Voice features require a system-wide installation of **FFmpeg**.

***

### Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

Please feel free to fork the repo and submit a pull request.

***

### Credits

* **NLTK chat events inspiration:** [YungSchmeg's discord-chat-bot-nltk](https://github.com/YungSchmeg/discord-chat-bot-nltk)
