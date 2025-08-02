# C:/Development/Projects/Demented-Discord-Bot/cogs/ai.py

import os
import logging
import random
import json
import discord
from discord import app_commands
from discord.ext import commands, tasks
from collections import deque
from typing import List, Dict, Any, Union, Optional

from data.utils import get_config_value
from data.session_manager import cached_http_get
from utils.prompts import SYSTEM_PROMPT, CREATOR_CONTEXT_PROMPT, BOT_MOOD_PROMPT, USER_SENTIMENT_PROMPT
from data.database_manager import (
    add_user_fact, get_user_facts, get_user_sentiment, update_user_sentiment,
    get_all_guilds_with_autonomy, get_server_config_value
)

logger = logging.getLogger('demented_bot.ai')


class ConversationManager:
    def __init__(self):
        self.histories = {}

    def get_history(self, channel_id: int, max_length: int) -> list:
        if channel_id not in self.histories:
            self.histories[channel_id] = deque(maxlen=max_length)
        if self.histories[channel_id].maxlen != max_length:
            self.histories[channel_id] = deque(self.histories[channel_id], maxlen=max_length)
        return list(self.histories[channel_id])

    def add_to_history(self, channel_id: int, role: str, content: str, max_length: int):
        if channel_id not in self.histories or self.histories[channel_id].maxlen != max_length:
            self.histories[channel_id] = deque(maxlen=max_length)
        self.histories[channel_id].append({"role": role, "content": content})


class AICog(commands.Cog, name="AI"):
    """Handles conversational AI interactions and autonomous behavior."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.conversation_manager = ConversationManager()
        self.boredom = 0.0
        self.autonomy_enabled = get_config_value(bot, "AUTONOMY_SETTINGS.ENABLED", False)
        # --- MODIFICATION: Add state tracking for anti-spam ---
        self.last_autonomously_tagged_user: Dict[int, int] = {}

        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. AI features will be disabled.")

        if self.autonomy_enabled:
            self.autonomy_loop.start()

    def cog_unload(self):
        """Gracefully stop the background task when the cog is unloaded."""
        if self.autonomy_enabled:
            self.autonomy_loop.cancel()

    def _get_mood_description(self) -> str:
        """Translates the boredom score into a mood description for the AI."""
        if self.boredom > 15:
            return "Extremely Irritable and Restless"
        if self.boredom > 10:
            return "Bored and looking for something to do"
        if self.boredom > 5:
            return "Slightly bored"
        return "Content and Attentive"

    def _get_sentiment_description(self, score: float) -> str:
        """Translates a user's sentiment score into a description for the AI."""
        if score > 5:
            return "This is one of my favorite users. Be extra witty and charming."
        if score > 2:
            return "I like this user. Be friendly."
        if score < -5:
            return "I strongly dislike this user. Be dismissive and condescending."
        if score < -2:
            return "I dislike this user. Be sarcastic and curt."
        return "Neutral. Standard interaction."

    def _format_history_for_gemini(self, history: list) -> list:
        gemini_contents = []
        for item in history:
            role = "model" if item["role"] == "assistant" else "user"
            gemini_contents.append({"role": role, "parts": [{"text": item["content"]}]})
        return gemini_contents

    async def _get_gemini_response(self, contents: list, memory_context: str = "", is_creator: bool = False,
                                   structured_response: bool = False) -> Union[str, Dict[str, Any]]:
        """
        Gets a response from the Gemini API.
        Can request a simple string or a structured JSON object.
        """
        if not self.api_key:
            return "My AI features are currently disabled by the bot owner."

        api_base_endpoint = get_config_value(self.bot, "AI_SETTINGS.API_ENDPOINT")
        model = get_config_value(self.bot, "AI_SETTINGS.DEFAULT_MODEL", "gemini-1.5-flash")
        api_url = f"{api_base_endpoint.strip('/')}/{model}:generateContent?key={self.api_key}"

        mood_desc = self._get_mood_description()
        mood_context = BOT_MOOD_PROMPT.format(mood_desc=mood_desc)

        final_system_prompt = SYSTEM_PROMPT + mood_context + memory_context
        if is_creator:
            final_system_prompt += CREATOR_CONTEXT_PROMPT

        generation_config = {"temperature": 0.9, "topK": 1, "topP": 1, "maxOutputTokens": 2048, "stopSequences": []}
        if structured_response:
            generation_config["responseMimeType"] = "application/json"
            # The specific prompt for the structured response is now added in the calling function
            # to allow for different kinds of structured requests.

        payload = {"contents": contents, "systemInstruction": {"parts": {"text": final_system_prompt}},
                   "generationConfig": generation_config}

        response_data = await cached_http_get(api_url, json_data=payload, method="post", ttl_seconds=0)

        if response_data and "candidates" in response_data and response_data["candidates"]:
            try:
                raw_text = response_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if structured_response:
                    try:
                        return json.loads(raw_text)
                    except json.JSONDecodeError:
                        logger.error(f"AI failed to return valid JSON. Raw response: {raw_text}")
                        # Provide a default structure on failure
                        return {"response_text": raw_text, "users_to_tag": [], "found_fact": False, "fact_text": None}
                else:
                    return raw_text
            except (KeyError, IndexError) as e:
                logger.error(f"Could not parse Gemini response: {e} | Response: {response_data}")

        logger.warning(f"Failed to get a valid response from the Gemini API. Response: {response_data}")
        fallback_response = "I'm sorry, I had a brain fart and couldn't think of a response. Try again?"
        if structured_response:
            return {"response_text": fallback_response, "users_to_tag": [], "found_fact": False, "fact_text": None}
        return fallback_response

    # ... (voice greeting methods remain unchanged) ...
    async def get_voice_greeting(self, user_name: str) -> str:
        """Generates a short, witty greeting for joining a voice channel."""
        prompt = (
            f"You are about to join a voice channel where the user '{user_name}' is waiting. "
            "Generate a short, witty, and slightly unhinged greeting. "
            "Keep it under 15 words. Examples: 'Did someone order a catastrophe?', "
            f"'I was summoned. This better be good, {user_name}.', 'Alright, who disturbed my slumber?'"
        )
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        return await self._get_gemini_response(contents) or f"Hello, {user_name}. I have arrived."

    async def get_nice_voice_greeting(self, user_name: str) -> str:
        """Generates a short, friendly greeting for joining a voice channel."""
        prompt = (
            f"You are about to join a voice channel to greet the user '{user_name}'. "
            "Generate a short, genuinely friendly, and welcoming greeting. "
            "Keep it under 15 words. Examples: 'Hey, {user_name}! Glad I could join you.', "
            "'What's up, everyone? Hope you're having a good one.'"
        )
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        return await self._get_gemini_response(contents) or f"Hey, {user_name}!"

    async def get_mean_voice_greeting(self, user_name: str) -> str:
        """Generates a short, insulting greeting for joining a voice channel."""
        prompt = (
            f"You are about to join a voice channel to insult the user '{user_name}'. "
            "Generate a short, witty, and unhinged insult. "
            "Keep it under 15 words. Examples: 'I heard mediocrity and came as fast as I could.', "
            f"'Oh great, it's {user_name}. Don't you all have better things to do?'"
        )
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        return await self._get_gemini_response(contents) or f"Ugh, fine. I'm here, {user_name}."

    async def get_conversational_response(self, message: discord.Message, mentioned_users: List[discord.Member],
                                          sentiment_change: float = 0.0) -> Dict[str, Any]:
        """Gets a contextual AI response, aware of mentioned users, and returns a structured object."""
        self.boredom = max(0, self.boredom - 2.0)
        user_id = message.author.id
        is_creator = user_id == self.bot.creator_id
        update_user_sentiment(user_id, sentiment_change)

        channel_id, author_name, user_input = message.channel.id, message.author.display_name, message.clean_content.replace(
            f"@{self.bot.user.name}", "").strip()
        max_history = get_config_value(self.bot, "AI_SETTINGS.MAX_HISTORY_LENGTH", 8)

        # Build a rich context including the author and all mentioned users
        author_facts = get_user_facts(user_id, limit=3)
        author_sentiment_score = get_user_sentiment(user_id)
        memory_context = ""
        if author_facts:
            memory_context += f"\n\n--- Things to remember about {author_name} (the speaker) ---\n- " + "\n- ".join(
                author_facts)
        memory_context += USER_SENTIMENT_PROMPT.format(user_name=author_name,
                                                       sentiment_desc=self._get_sentiment_description(
                                                           author_sentiment_score))

        if mentioned_users:
            memory_context += "\n\n--- Other users were mentioned in this message ---"
            for user in mentioned_users:
                if user.id == user_id: continue
                user_facts = get_user_facts(user.id, limit=3)
                user_sentiment = get_user_sentiment(user.id)
                memory_context += f"\n- User '{user.display_name}':"
                memory_context += f"\n  - My sentiment towards them: {self._get_sentiment_description(user_sentiment)}"
                if user_facts:
                    memory_context += "\n  - Known facts: " + ", ".join(user_facts)
            memory_context += "\nFeel free to use this information in your response and mention them by name if relevant."

        self.conversation_manager.add_to_history(channel_id, "user", f"{author_name}: {user_input}", max_history)
        history = self.conversation_manager.get_history(channel_id, max_history)
        gemini_contents = self._format_history_for_gemini(history)

        # Add the specific instructions for the structured response
        memory_context += (
            "\n\nIMPORTANT: Your response MUST be a valid JSON object with two keys: "
            "'response_text' (a string containing your conversational reply) and "
            "'users_to_tag' (a list of strings, where each string is the exact display name of a user you talked about in your response). "
            "Example: {\"response_text\": \"I heard David is great at that!\", \"users_to_tag\": [\"David\"]}"
        )

        ai_response_data = await self._get_gemini_response(
            gemini_contents,
            memory_context=memory_context,
            is_creator=is_creator,
            structured_response=True
        )

        if ai_response_data and ai_response_data.get("response_text"):
            self.conversation_manager.add_to_history(channel_id, "assistant", ai_response_data["response_text"],
                                                     max_history)

        return ai_response_data

    async def assess_and_remember_fact(self, message: discord.Message) -> Optional[str]:
        """
        Analyzes a user's message to see if it contains a new, noteworthy fact.
        If so, saves it to the database and returns a confirmation message.
        """
        user = message.author
        user_message = message.clean_content

        fact_assessment_prompt = f"""
        The user '{user.display_name}' just said the following:
        "{user_message}"

        Your task is to analyze this message for any new, noteworthy personal information or facts about the user.
        A noteworthy fact is something personal, a preference, a detail about their life, or a significant event.
        Do NOT extract opinions about others, questions, or generic statements.

        Examples of noteworthy facts to extract:
        - "I'm learning to play the piano." -> "Is learning to play the piano."
        - "My favorite color is blue." -> "Favorite color is blue."
        - "I have a cat named Whiskers." -> "Has a cat named Whiskers."
        - "I work as a software engineer." -> "Works as a software engineer."

        Examples of what is NOT a noteworthy fact:
        - "I think this bot is cool." (Opinion about the bot)
        - "What time is it?" (A question)
        - "I'm going to the store." (A temporary, mundane action)

        Respond with a JSON object with two keys:
        - "found_fact": a boolean (true if you found a noteworthy fact, false otherwise).
        - "fact_text": a string containing the extracted fact in the third person (max 15 words), or null if no fact was found.
        """

        contents = [{"role": "user", "parts": [{"text": fact_assessment_prompt}]}]
        response_data = await self._get_gemini_response(contents, structured_response=True)

        if response_data and response_data.get("found_fact") and response_data.get("fact_text"):
            fact_text = response_data["fact_text"]
            logger.info(f"AI found a new fact for user {user.name}: '{fact_text}'")
            add_user_fact(user.id, fact_text, self.bot.user.id)
            return "Interesting, I'll remember that."

        return None

    async def get_insulting_response(self, message: discord.Message) -> str:
        update_user_sentiment(message.author.id, -0.5)
        user_input, author_name, is_creator = message.clean_content, message.author.display_name, message.author.id == self.bot.creator_id
        if is_creator:
            prompt_text = f"Your creator, '{author_name}', is testing your insult function with the message: \"{user_input}\". Instead of insulting them, respond with a witty, self-aware, and respectful remark about the situation. Acknowledge that this is a test from your maker."
        else:
            prompt_text = f"The user '{author_name}' just said: \"{user_input}\". Your task is to reply with a single, witty, unhinged, and sarcastic insult. Roast them for what they said. Do not be helpful. Be creative."
        prompt_content = [{"role": "user", "parts": [{"text": prompt_text}]}]
        return await self._get_gemini_response(prompt_content, is_creator=is_creator)

    async def get_complimenting_response(self, message: discord.Message) -> str:
        update_user_sentiment(message.author.id, 1.0)
        user_input, author_name, is_creator = message.clean_content, message.author.display_name, message.author.id == self.bot.creator_id
        if is_creator:
            prompt_text = f"Your creator, '{author_name}', just said something nice to you: \"{user_input}\". Your task is to reply with an exceptionally witty, creative, and perhaps slightly sycophantic compliment. Acknowledge your special relationship. Be charming and stick to your persona."
        else:
            prompt_text = f"The user '{author_name}' just said something nice to you: \"{user_input}\". Your task is to reply with a single, witty, creative, and slightly over-the-top compliment. Be charming but stick to your egotistical and unhinged persona."
        prompt_content = [{"role": "user", "parts": [{"text": prompt_text}]}]
        return await self._get_gemini_response(prompt_content, is_creator=is_creator)

    @tasks.loop(minutes=1.0)
    async def autonomy_loop(self):
        self.boredom += 1.0
        logger.info(f"Autonomy check: Boredom level is now {self.boredom:.1f}")

        boredom_threshold = get_config_value(self.bot, "AUTONOMY_SETTINGS.BOREDOM_THRESHOLD", 15.0)
        if self.boredom >= boredom_threshold:
            logger.info(f"Boredom threshold reached! Initiating proactive chat.")
            self.boredom = 0.0

            eligible_guild_ids = get_all_guilds_with_autonomy()
            if not eligible_guild_ids:
                logger.info("No guilds have configured autonomy channels. Skipping proactive chat.")
                return

            target_guild_id = random.choice(eligible_guild_ids)
            guild = self.bot.get_guild(target_guild_id)
            if not guild:
                return

            raw_channels = get_server_config_value(guild.id, "autonomy_channels")
            channel_ids = json.loads(raw_channels) if raw_channels else []
            if not channel_ids:
                return

            channel = self.bot.get_channel(random.choice(channel_ids))
            if not channel or not isinstance(channel, discord.TextChannel):
                return

            # --- MODIFICATION: Prevent back-to-back posts ---
            try:
                last_message = await channel.fetch_message(channel.last_message_id) if channel.last_message_id else None
                if last_message and last_message.author.id == self.bot.user.id:
                    logger.info(f"Skipping autonomous message in #{channel.name}: I was the last one to speak.")
                    return
            except (discord.NotFound, discord.Forbidden):
                logger.warning(f"Could not fetch last message in #{channel.name}. Skipping to be safe.")
                return

            # --- MODIFICATION: Prevent consecutive user tags ---
            last_tagged_id = self.last_autonomously_tagged_user.get(channel.id)
            online_members = [
                m for m in channel.members
                if not m.bot and m.status != discord.Status.offline and m.id != last_tagged_id
            ]
            target_user = random.choice(online_members) if online_members else None

            if target_user:
                prompt_text = f"You are feeling bored. Start a conversation with the user '{target_user.display_name}' to entertain yourself. Ask them an absurd or interesting question."
            else:
                # --- SUGGESTION: Add logging for this case ---
                if online_members:
                    logger.info(f"No valid, non-consecutive users to target in #{channel.name}. Posting a generic message.")
                # --- END SUGGESTION ---
                prompt_text = "You are feeling bored. Say something interesting or absurd to the channel to stir up conversation."

            async with channel.typing():
                conversation_starter = await self._get_gemini_response(
                    [{"role": "user", "parts": [{"text": prompt_text}]}])
                if conversation_starter:
                    if target_user:
                        await channel.send(f"{target_user.mention}, {conversation_starter}")
                        # --- MODIFICATION: Update the state tracking ---
                        self.last_autonomously_tagged_user[channel.id] = target_user.id
                        logger.info(f"Posted autonomous message in #{channel.name} targeting {target_user.name}.")
                    else:
                        await channel.send(conversation_starter)
                        logger.info(f"Posted autonomous message in #{channel.name} with no target.")

    @autonomy_loop.before_loop
    async def before_autonomy_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="ask", description="Ask the AI a question directly.")
    async def ask(self, interaction: discord.Interaction, *, question: str):
        if not self.api_key:
            await interaction.response.send_message("My AI features are currently disabled.", ephemeral=True)
            return
        await interaction.response.defer()
        gemini_contents = [{"role": "user", "parts": [{"text": question}]}]
        ai_response = await self._get_gemini_response(gemini_contents)
        await interaction.followup.send(f"**Question:** {question}\n**Answer:** {ai_response}")

    @app_commands.command(name="remember", description="Stores a fact about a user for the AI to remember.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def remember(self, interaction: discord.Interaction, user: discord.Member, fact: str):
        if add_user_fact(user.id, fact, interaction.user.id):
            await interaction.response.send_message(f"Okay, I'll remember that about {user.mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("I tried to remember that, but my brain is full of bees.",
                                                    ephemeral=True)

    @app_commands.command(name="soul-status", description="Check my current internal state (for debug).")
    @commands.is_owner()
    async def soul_status(self, interaction: discord.Interaction,
                          user: discord.Member = None):
        """Displays the bot's current mood and sentiment towards a user."""
        target_user = user or interaction.user
        await interaction.response.defer(ephemeral=True)

        mood = self._get_mood_description()
        boredom = self.boredom
        sentiment_score = get_user_sentiment(target_user.id)
        sentiment_desc = self._get_sentiment_description(sentiment_score)

        embed = discord.Embed(
            title="🧠 My Internal State",
            color=discord.Color.purple()
        )
        embed.add_field(name="Current Mood", value=mood, inline=False)
        embed.add_field(name="Boredom Level", value=f"{boredom:.2f}", inline=False)
        embed.add_field(
            name=f"Sentiment towards {target_user.display_name}",
            value=f"**Score:** {sentiment_score:.2f}\n**Interpretation:** {sentiment_desc}",
            inline=False
        )
        embed.set_footer(text="This information is only visible to you.")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AICog(bot))