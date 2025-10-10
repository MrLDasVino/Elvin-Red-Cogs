import random
from datetime import datetime, timedelta

import discord
from discord.ext import tasks
from redbot.core import commands, Config, bank

# Banner image URLs – replace these placeholders with your actual image links
SEED_BANNER = "https://files.catbox.moe/i1787b.png"
PLANT_BANNER = "https://files.catbox.moe/7btmdw.png"
LIST_BANNER = "https://files.catbox.moe/43lzl6.png"
REWARD_BANNERS = {
    "currency": "https://files.catbox.moe/bn35ib.png",
    "prompt":   "https://files.catbox.moe/6oqu0n.png",
    "fortune":  "https://files.catbox.moe/z1gy0f.png",
    "advice":   "https://files.catbox.moe/3nr7zo.png",
}

PROMPTS = [
    "Write a letter to your future self.",
    "Describe a world where trees glow at night.",
    "Create a 50-word mystery scene.",
    "Invent a new holiday and its traditions.",
    "Sketch a dialogue between a human and an AI.",
    "Write a scene where a character wakes up in a desert with no memory of how they arrived.",
    "Describe a floating island nation and its unique customs.",
    "Imagine a future where plants communicate through color changes.",
    "Write a dialogue between two rival time travelers negotiating a peace treaty.",
    "Craft a letter from a soldier on an alien planet to their family on Earth.",
    "Describe a city built entirely from glass and its hidden dangers.",
    "Invent a holiday celebrated by robots and its unusual traditions.",
    "Write a diary entry of someone living under the ocean.",
    "Sketch a marketplace where people trade memories instead of goods.",
    "Create a 100-word mystery that begins with a missing shoe.",
    "Write a recipe for happiness using metaphorical ingredients.",
    "Describe a world where everyone has a visible countdown timer above their heads.",
    "Imagine a conversation between a ghost and a living relative.",
    "Write a scene set in a train that never stops moving.",
    "Invent a sport played by aerial creatures in the sky.",
    "Craft a bedtime story told by an artificial intelligence to children.",
    "Describe a library that contains every book ever thought of but none ever published.",
    "Write a short biography of a mythical creature that lives in city sewers.",
    "Imagine a world where colors taste like different fruits.",
    "Create a dialogue between a mirror and the person looking into it.",
    "Write a flash fiction piece from the perspective of a raindrop falling on a rooftop.",
    "Describe a garden that grows memories instead of plants.",
    "Invent a device that translates emotions into music and its inventor's regrets.",
    "Write a postcard from a tourist visiting the Moon.",
    "Sketch a conversation between two stars witnessing Earth's history.",
    "Write a scene where a day lasts only five minutes.",
    "Explain a ritual that summons the wind and its consequences.",
    "Create a poem about the silence between two heartbeats.",
    "Describe a city at the bottom of a crystal-clear lake.",
    "Write a story that starts at the end and works backwards.",
    "Imagine a library where books rewrite themselves based on readers' thoughts.",
    "Craft a dialogue between a human and their future self.",
    "Describe the taste of memories long forgotten.",
    "Write a scene in which shadows come to life at night.",
    "Invent a game where players bet on the outcome of dreams.",
    "Write a letter from a child to their future self 50 years ahead.",
    "Describe the interior of a clock that counts lives instead of time.",
    "Create a 200-word flashback that reveals a character's secret.",
    "Sketch an ecosystem on a planet with no sunlight.",
    "Imagine a world where everyone must tell a lie once a day.",
    "Write a conversation between two abandoned robots.",
    "Describe an island that changes shape daily.",
    "Invent a perfume that evokes forgotten memories.",
    "Write a scene set in a café at the edge of a black hole.",
    "Craft a story that spans a single breath.",
    "Describe the sound of colors clashing in the sky.",
    "Imagine a society where poetry is currency.",
    "Write a flash fiction about a disappearing village.",
    "Sketch an argument between morning and night.",
    "Create a dialogue between a dream and reality.",
    "Write a letter from a tree to the person who planted it.",
    "Describe a festival that celebrates the end of the world.",
    "Invent a sport that uses gravity as a playing field.",
    "Write a 60-word horror scene in an abandoned hospital.",
    "Imagine a world where music controls the weather.",
    "Craft a scene where gravity suddenly reverses in a city.",
    "Describe a mentor who teaches magic through cooking.",
    "Write a conversation between a statue and the sculptor's descendant.",
    "Invent a language spoken only by birds.",
    "Sketch a journey across a desert made of glass.",
    "Create a monologue from a lighthouse keeper on Mars.",
    "Describe a mask that reveals someone's true self.",
    "Write a flash fiction about a book that writes its own ending.",
    "Imagine a world where noses detect emotions.",
    "Craft a letter from an explorer descending into Earth's core.",
    "Describe a carnival where every ride tells a story.",
    "Write a scene where televisions predict your future.",
    "Invent a potion that lets you speak to the dead and its side effects.",
    "Sketch the life of a clockmaker who controls time.",
    "Create a dialogue between a rainstorm and the clouds.",
    "Write a 150-word scene set in a city without gravity.",
    "Describe a world where echoes have memories.",
    "Imagine a creature born from the stars and its first steps on Earth.",
    "Craft a story that unfolds through newspaper headlines.",
    "Describe a painting that changes every time you look away.",
    "Write a poem about the smell of midnight.",
    "Invent a device that captures dreams and sells them.",
    "Sketch a world where books grow on trees.",
    "Write a letter from a future AI to its creator.",
    "Describe the taste of the first snowfall.",
    "Create a dialogue between fire and ice.",
    "Write a scene where all water vanishes for a day.",
    "Imagine a city built on the backs of giant turtles.",
    "Craft a flash fiction about the last breath of a dying star.",
    "Describe a mirror that shows alternate realities.",
    "Write a monologue from a ghost who haunts libraries.",
    "Invent a holiday celebrating a myth you've created.",
    "Sketch a society governed by poets instead of politicians.",
    "Write a 100-word mystery about a locked room.",
    "Describe a symphony performed by the ocean waves.",
    "Imagine a world where seasons have personalities.",
    "Craft a dialogue between a labyrinth and its wanderer.",
    "Describe the life cycle of a thought.",
    "Write a flash fiction set in an eternal night.",
    "Invent a creature that feeds on human stories.",
    "Sketch a desert where the sand sings songs.",
    "Write a letter from a citizen of a world with no shadows.",
    "Describe a machine that builds towers to the sky.",
    "Imagine a festival where people swap identities for a day.",
    "Craft a scene where gravity is optional."
]
    
FORTUNES = [
    "A pleasant surprise is around the corner.",
    "Change begins at the end of your comfort zone.",
    "Someone you least expect will bring joy today.",
    "Great achievements start with small steps.",
    "Your persistence will soon pay off.",
    "A pleasant surprise is waiting for you.",
    "Your hard work will soon pay off in unexpected ways.",
    "New opportunities are on the horizon.",
    "An old acquaintance will re-enter your life.",
    "Kindness shown to others will return to you.",
    "A fresh start will become available to you.",
    "Your creativity will lead to real success.",
    "Trust your instincts; they will guide you well.",
    "A small act of generosity will create a ripple effect.",
    "Happiness begins with a single step forward.",
    "Your positive attitude will attract good fortune.",
    "A chance encounter will change your outlook.",
    "Patience will reward you in due time.",
    "You are about to embark on a new adventure.",
    "A meaningful friendship is just around the corner.",
    "Your smile will brighten someone's day.",
    "Courage will open doors you never imagined.",
    "An opportunity to learn will present itself.",
    "Balance in life will bring you peace.",
    "A financial blessing is heading your way.",
    "Your persistence will overcome current challenges.",
    "New knowledge will empower your choices.",
    "A heartfelt conversation will strengthen a bond.",
    "Joy will find you when you least expect it.",
    "You will discover a hidden talent.",
    "An exciting journey is on your path.",
    "Your compassion will make a difference.",
    "A fresh perspective will solve an old problem.",
    "Serendipity will lead you to something wonderful.",
    "Your generosity will be remembered.",
    "An inspiring idea will spark creativity.",
    "Good news will arrive in the mail.",
    "You will overcome a lingering worry.",
    "A new friendship will enrich your life.",
    "Your kindness will open unexpected doors.",
    "An adventure in nature will rejuvenate you.",
    "Your wit will delight those around you.",
    "A small risk will bring big rewards.",
    "You will find clarity in a confusing situation.",
    "A moment of stillness will bring insight.",
    "Your optimism will lead to success.",
    "A creative project will receive praise.",
    "You will achieve a long-sought goal.",
    "A timely reminder will guide your decisions.",
    "Your efforts will inspire others.",
    "A surprise gift will brighten your day.",
    "You will experience a wave of inspiration.",
    "An unexpected call will bring good news.",
    "Your dedication will be recognized.",
    "You will make someone’s day with your words.",
    "A warm connection will deepen soon.",
    "You will learn something valuable today.",
    "An upcoming event will bring joy.",
    "Your sincerity will earn trust.",
    "A new chapter begins with a single page.",
    "Your laughter will be contagious.",
    "You will find beauty in simplicity.",
    "A moment of courage will change everything.",
    "Your dreams are closer than they appear.",
    "An act of kindness will find its way back.",
    "You will receive an unexpected compliment.",
    "Your insights will help someone in need.",
    "A flash of inspiration will guide your path.",
    "You will make a breakthrough soon.",
    "A joyful surprise awaits you at home.",
    "Your generosity will sow seeds of happiness.",
    "An overdue recognition is on the way.",
    "You will embrace a new beginning.",
    "A simple change will bring great joy.",
    "You will find harmony in all you do.",
    "A new friendship will blossom quickly.",
    "Your efforts will lead to a surprising outcome.",
    "A peaceful moment will restore your spirit.",
    "Your next idea will be your best yet.",
    "An opportunity to travel will present itself.",
    "You will conquer a fear soon.",
    "A comforting message will arrive unexpectedly.",
    "Your talents will be celebrated.",
    "A new hobby will bring you delight.",
    "You will find balance in unexpected ways.",
    "An inspiring person will cross your path.",
    "Your words will have a positive impact.",
    "A new perspective will invigorate you.",
    "Your resilience will see you through.",
    "A long-awaited decision will go your way.",
    "Your kindness will light up the room.",
    "A small discovery will spark excitement.",
    "Your patience will lead to a big win.",
    "A cherished memory will bring you comfort.",
    "Your next step will feel like destiny.",
    "A supportive friend will appear just when needed.",
    "Your heart will guide you to happiness.",
    "A chance for growth is heading your way.",
    "Your spirit will shine bright today.",
    "A fortunate coincidence will delight you.",
    "Your inner strength will be your ally.",
    "A new goal will inspire you.",
    "Your journey will take a positive turn.",
    "A small victory will boost your confidence.",
    "Your optimism will attract wonderful surprises."
]
    
ADVICE = [
    "Remember to take breaks and breathe deeply.",
    "A clear mind makes better decisions.",
    "Collaboration often sparks the best ideas.",
    "Small daily habits lead to big results.",
    "Listen more than you speak.",
    "Take a moment each day to breathe deeply and center yourself.",
    "Focus on progress rather than perfection.",
    "Listen more than you speak to truly understand others.",
    "Set clear boundaries to protect your energy.",
    "Embrace mistakes as opportunities to learn.",
    "Prioritize tasks that align with your core values.",
    "Practice gratitude to shift your mindset to abundance.",
    "Break big goals into small, manageable steps.",
    "Be patient with yourself during challenging times.",
    "Celebrate even the smallest victories.",
    "Stay curious and ask questions freely.",
    "Trust your intuition when making decisions.",
    "Allocate time for rest to avoid burnout.",
    "Make time for activities that spark joy.",
    "Respect your own pace; progress is personal.",
    "Be honest with yourself about your needs.",
    "Surround yourself with supportive people.",
    "Express appreciation to those who help you.",
    "Reflect on your wins at the end of each week.",
    "Let go of what you cannot control.",
    "Practice empathy to build stronger connections.",
    "Keep learning something new every day.",
    "Take regular breaks to recharge your focus.",
    "Speak kindly to yourself; self-talk matters.",
    "Document your thoughts in a journal for clarity.",
    "Set realistic deadlines to maintain momentum.",
    "Protect your mental space from negative influences.",
    "Invest time in hobbies that inspire you.",
    "Ask for help when the task is too big.",
    "Maintain a consistent sleep schedule for well-being.",
    "Use setbacks as fuel for future success.",
    "Plan ahead but remain flexible to change.",
    "Practice one act of kindness each day.",
    "Challenge yourself to step outside your comfort zone.",
    "Limit multitasking to improve concentration.",
    "Stand up for your beliefs with confidence.",
    "Prioritize tasks based on impact, not urgency.",
    "Make time for self-reflection regularly.",
    "Keep a positive outlook in the face of adversity.",
    "Trust that you have the resources to adapt.",
    "Learn to say no without guilt.",
    "Maintain curiosity about the world around you.",
    "Practice mindful eating to nourish your body.",
    "Declutter your environment to clear your mind.",
    "Stay focused on what you can influence.",
    "Visualize success to motivate your actions.",
    "Review your goals every month for accountability.",
    "Share your successes to inspire others.",
    "Take responsibility for your happiness.",
    "Embrace change as a pathway to growth.",
    "Guard your time like your most valuable asset.",
    "Seek feedback to improve continuously.",
    "Balance work with play to sustain creativity.",
    "Cultivate resilience through daily challenges.",
    "Spend time in nature to restore balance.",
    "Keep your promises to build trust.",
    "Start each day with a clear intention.",
    "Invest in relationships that uplift you.",
    "Face fears one small step at a time.",
    "Reflect on lessons learned during setbacks.",
    "Practice active listening in every conversation.",
    "Be open to adapting your goals as needed.",
    "Express gratitude to yourself for your efforts.",
    "Seek out mentors to guide your journey.",
    "Take responsibility instead of placing blame.",
    "Embrace simplicity to reduce stress.",
    "Set boundaries on social media use.",
    "Nurture your creativity with daily practice.",
    "Focus on solutions rather than dwelling on problems.",
    "Celebrate others' successes as well as your own.",
    "Make a habit of reviewing your finances.",
    "Find comfort in routine during chaotic times.",
    "Approach challenges with a beginner's mindset.",
    "Let go of perfectionism to finish tasks sooner.",
    "Stay open to constructive criticism.",
    "Plan times for reflection and adjustment.",
    "Practice self-compassion in moments of doubt.",
    "Surprise yourself by trying something new.",
    "Listen to your body’s cues for rest or action.",
    "Build habits that reinforce your long-term vision.",
    "Express your creativity in multiple forms.",
    "Set aside time for meaningful conversations.",
    "Trust that consistency cultivates change.",
    "Document your achievements to boost confidence.",
    "Allow yourself to pause and recalibrate.",
    "Keep your workspace organized to boost productivity.",
    "Use affirmations to reinforce positive beliefs.",
    "Seek balance between giving and receiving.",
    "Invest in skills that align with your purpose.",
    "Remind yourself daily of your core strengths.",
    "Maintain integrity even when no one is watching.",
    "Cultivate a mindset of lifelong learning.",
    "Check in with friends and family regularly.",
    "Use challenges to refine your strategies.",
    "Stay adaptable in an ever-changing world.",
    "Practice deep listening before responding.",
    "Value progress over immediate perfection.",
    "Take mindful pauses before making big choices.",
    "Keep a learner’s curiosity in every situation.",
    "Remind yourself that every day is a fresh start."
]
    
MIN_CREDITS = 100
MAX_CREDITS = 300

class FortuneGarden(commands.Cog):
    """
    FortuneGarden — users earn seeds by chatting (max one per hour),
    then plant seeds that bloom into random rewards with rich embeds.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210987)
        default_guild = {
            "fortunes": {},
            "min_credits": MIN_CREDITS,
            "max_credits": MAX_CREDITS,
        }
        default_member = {"seeds": 0, "last_earned": None}
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        self.bloom_loop.start()

    def cog_unload(self):
        self.bloom_loop.cancel()

    @tasks.loop(seconds=60.0)
    async def bloom_loop(self):
        now = datetime.utcnow()
        all_guilds = await self.config.all_guilds()

        for guild_id, data in all_guilds.items():
            fortunes = data["fortunes"]
            min_amt = data.get("min_credits", MIN_CREDITS)
            max_amt = data.get("max_credits", MAX_CREDITS)            
            changed = False

            for fid, info in list(fortunes.items()):
                # skip already processed or not yet due
                bloom_dt = datetime.fromisoformat(info["bloom_time"])
                if info.get("processed") or now < bloom_dt:
                    continue

                try:
                    guild = self.bot.get_guild(int(guild_id))
                    channel = guild and guild.get_channel(info["channel_id"])
                    member = guild and guild.get_member(info["owner_id"])

                    if not channel or not member:
                        # channel/guild/member gone → drop the seed
                        fortunes.pop(fid)
                        changed = True
                        continue

                    # pick reward
                    reward_type = random.choice(["currency", "prompt", "fortune", "advice"])
                    if reward_type == "currency":
                        amount = random.randint(min_amt, max_amt)
                        await bank.deposit_credits(member, amount)
                        currency = await bank.get_currency_name(member.guild, amount)
                        desc = f"💰 You received **{amount}** {currency}!"
                    elif reward_type == "prompt":
                        desc = f"🖋️ Prompt: {random.choice(PROMPTS)}"
                    elif reward_type == "fortune":
                        desc = f"🔮 Fortune: {random.choice(FORTUNES)}"
                    else:
                        desc = f"💡 Advice: {random.choice(ADVICE)}"

                    embed = discord.Embed(
                        title="🌸 Your Fortune Seed Has Bloomed!",
                        description=desc,
                        colour=discord.Colour.random()
                    )
                    embed.set_image(url=REWARD_BANNERS[reward_type])

                    await channel.send(content=member.mention, embed=embed)

                    # mark processed only after successful send
                    fortunes[fid]["processed"] = True
                    changed = True

                except Exception as exc:
                    # catch all errors, log if desired, and drop the bad seed
                    # logging.warning(f"Failed to bloom seed {fid}: {exc}")
                    fortunes.pop(fid)
                    changed = True

            if changed:
                await self.config.guild_from_id(guild_id).fortunes.set(fortunes)


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
    
        member_conf = self.config.member(message.author)
        data = await member_conf.all()
        last = data["last_earned"]
        now = datetime.utcnow()
    
        if last and now - datetime.fromisoformat(last) < timedelta(hours=1):
            return
    
        if random.random() < 0.05:
            new_count = data["seeds"] + 1
            await member_conf.seeds.set(new_count)
            await member_conf.last_earned.set(now.isoformat())
    
            prefix = (await self.bot.get_prefix(message))[0]
            await message.channel.send(
                f"{message.author.mention} 🌱 You discovered a fortune seed! "
                f"You now have **{new_count}** seed{'s' if new_count != 1 else ''}.\n"
                f"Use `{prefix}plantfortune` to plant one!"
            )


    @commands.guild_only()
    @commands.command(
        name="fortuneseeds",                             
        help="Show how many fortune seeds you or another member has."
    )
    async def fortuneseeds(self, ctx, member: discord.Member = None):
        """
        Show how many fortune seeds a user has.
        """
        # default to command author if no member specified
        member = member or ctx.author

        seeds = await self.config.member(member).seeds()
        embed = discord.Embed(
            title="🌱 Fortune Seeds",
            description=(
                f"{member.mention} has **{seeds}** fortune seed"
                f"{'s' if seeds != 1 else ''}."
            ),
            colour=discord.Colour.random()
        )
        embed.set_image(url=SEED_BANNER)
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command()
    async def plantfortune(self, ctx):
        """
        Plant a fortune seed (consumes 1 seed) that will bloom in 1–12 hours.
        """
        member_conf = self.config.member(ctx.author)
        seeds = await member_conf.seeds()
        if seeds < 1:
            return await ctx.send(
                f"{ctx.author.mention}, you have no fortune seeds! Chat more to earn some."
            )

        await member_conf.seeds.set(seeds - 1)
        delay = random.randint(1, 12)
        bloom_time = datetime.utcnow() + timedelta(hours=delay)
        fid = str(int(datetime.utcnow().timestamp() * 1000))

        new_seed = {
            "owner_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "bloom_time": bloom_time.isoformat(),
            "processed": False
        }

        guild_conf = self.config.guild(ctx.guild)
        fortunes = await guild_conf.fortunes()
        fortunes[fid] = new_seed
        await guild_conf.fortunes.set(fortunes)

        embed = discord.Embed(
            title="🌱 Seed Planted",
            description=(
                f"{ctx.author.mention}, your seed will bloom in **{delay}** hour(s)."
            ),
            colour=discord.Colour.random()
        )
        embed.add_field(name="Seed ID", value=fid, inline=True)
        embed.add_field(name="Seeds Left", value=f"{seeds - 1}", inline=True)
        embed.set_image(url=PLANT_BANNER)
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command()
    async def listfortunes(self, ctx):
        """List your planted fortune seeds and their statuses."""
        fortunes = await self.config.guild(ctx.guild).fortunes()
        now = datetime.utcnow()
        lines = []
        for fid, info in fortunes.items():
            if info["owner_id"] != ctx.author.id:
                continue
            bloom_dt = datetime.fromisoformat(info["bloom_time"])
            if info.get("processed"):
                status = "🌸 Bloomed"
            else:
                rem = bloom_dt - now
                hrs = int(rem.total_seconds() // 3600)
                mins = int((rem.total_seconds() % 3600) // 60)
                status = f"⌛ {hrs}h {mins}m left"
            lines.append(f"ID `{fid}` — {status}")

        if not lines:
            return await ctx.send("You have no active fortune seeds.")

        embed = discord.Embed(
            title="🌱 Your Planted Seeds",
            description="\n".join(lines),
            colour=discord.Colour.random()
        )
        embed.set_image(url=LIST_BANNER)
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command()
    async def removefortune(self, ctx, fid: str):
        """Remove one of your unbloomed fortune seeds by ID."""
        guild_conf = self.config.guild(ctx.guild)
        fortunes = await guild_conf.fortunes()
        info = fortunes.get(fid)
        if not info:
            return await ctx.send("No fortune seed with that ID.")
        if info["owner_id"] != ctx.author.id and not ctx.author.guild_permissions.manage_guild:
            return await ctx.send("You don't have permission to remove this seed.")
        fortunes.pop(fid)
        await guild_conf.fortunes.set(fortunes)
        await ctx.send(f"🗑️ Removed fortune seed `{fid}`.")
        
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @commands.command(
        name="setfortunepayout",
        help="Set the min and max credits granted when a seed blooms."
    )
    async def setfortunepayout(self, ctx, min_amt: int, max_amt: int):
        """
        Usage:  setfortunepayout <min> <max>
        Example: setfortunepayout 50 500
        """
        if min_amt < 0 or max_amt < min_amt:
            return await ctx.send("⚠️ Invalid range. Ensure 0 ≤ min ≤ max.")

        guild_conf = self.config.guild(ctx.guild)
        await guild_conf.min_credits.set(min_amt)
        await guild_conf.max_credits.set(max_amt)
        await ctx.send(f"✅ Fortune payout range updated to **{min_amt}**–**{max_amt}** credits.")
        
