from typing import NewType, Union

import discord

ALL_GOOD_TYPES = NewType('all_good_types', Union[
    discord.Member, discord.User, discord.TextChannel, discord.VoiceChannel, discord.GroupChannel,
    discord.Role, discord.Message, int, float, str])

EMOJI_NUMBERS = {
    0: "0️⃣",
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
    4: "4️⃣",
    5: "5️⃣",
    6: "6️⃣",
    7: "7️⃣",
    8: "8️⃣",
    9: "9️⃣",
    10: "🔟"
}

TEXT_EMOJI_NUMBERS = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "keycap_ten"
}
