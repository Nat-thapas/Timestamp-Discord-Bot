import calendar
import datetime
import json
import logging
import os
from textwrap import dedent

import ctparse
import discord
import dotenv
from dateutil.relativedelta import relativedelta
from sqlitedict import SqliteDict

import parsers

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s:%(levelname)s:%(name)s: %(message)s"
)

dotenv.load_dotenv()

is_development = os.getenv("DEV", "FALSE").lower() == "true"
if is_development:
    logging.info("Environment is detected as development")
    preview_guilds = list(map(int, os.getenv("PREVIEW_GUILDS", "").split(",")))
    if preview_guilds:
        logging.info(f"Commands will only be available on {preview_guilds}")
    else:
        preview_guilds = None
        logging.info("Commands will be available globally")
else:
    preview_guilds = None

users_db = SqliteDict(
    "database.sqlite",
    tablename="users",
    journal_mode="WAL",
    encode=json.dumps,
    decode=json.loads,
    autocommit=True,
    outer_stack=False,
)

with open("timezones_abbreviations.json") as tz_data_json_file:
    timezone_abbreviations_data = json.load(tz_data_json_file)

bot = discord.Bot()


@bot.event
async def on_ready():
    logging.info(f"{bot.user} is now ready.")


timestamp = bot.create_group(
    "timestamp", "Convert time to timestamp", guild_ids=preview_guilds
)


@timestamp.command(
    description="Convert time (in UTC by default) to timestamp, manual mode"
)
async def manual(
    ctx,
    day: discord.Option(int, min_value=1, max_value=31),
    month: discord.Option(int, min_value=1, max_value=12),
    year: discord.Option(
        int,
        "If input is between 0 and 100, it will be interpreted as 2 digits year number",
        min_value=0,
    ),
    hour: discord.Option(int, min_value=0, max_value=23),
    minute: discord.Option(int, min_value=0, max_value=59),
    second: discord.Option(
        int, "Optional, default to 0", min_value=0, max_value=59, default=0
    ),
    timezone: discord.Option(
        str,
        "±hh:mm, ±hh, ±h:mm, ±h or well-known abbreviations with standard/daylight option (CST/CDT, EST/EDT)",
        default="DEFAULT",
    ),
):
    if timezone == "DEFAULT":
        if ctx.author.id in users_db and "default_timezone" in users_db[ctx.author.id]:
            timezone = users_db[ctx.author.id]["default_timezone"]
        else:
            timezone = "+00:00"
    try:
        (
            tz_name,
            tz_offset_string,
            tz_offset_seconds,
        ) = parsers.parse_timezone_abbreviations(timezone, timezone_abbreviations_data)
    except ValueError:
        try:
            tz_name = ""
            tz_offset_string = timezone
            tz_offset_seconds = parsers.parse_timezone(timezone)
        except ValueError:
            await ctx.respond(
                "Invalid timezone format or unknown abbreviation, please make sure the input is correct and try again.",
                ephemeral=True,
            )
            return

    reference_time = datetime.datetime.utcnow() + relativedelta(
        seconds=tz_offset_seconds
    )
    if 0 <= year < 100:
        current_year = reference_time.year
        year = parsers.short_to_long_year(year, current_year)
    try:
        unix_time = round(
            calendar.timegm(
                datetime.datetime(
                    day=day,
                    month=month,
                    year=year,
                    hour=hour,
                    minute=minute,
                    second=second,
                ).timetuple()
            )
        )
        unix_time -= tz_offset_seconds  # We want UTC from user's input, so we need to offset the time opposite way
        await ctx.respond(
            dedent(
                f"""
                {f"Timezone: {tz_name} ({tz_offset_string})" if tz_name else ""}
                `<t:{unix_time}:F>` : <t:{unix_time}:F>
                `<t:{unix_time}:f>` : <t:{unix_time}:f>
                `<t:{unix_time}:D>` : <t:{unix_time}:D>
                `<t:{unix_time}:d>` : <t:{unix_time}:d>
                `<t:{unix_time}:T>` : <t:{unix_time}:T>
                `<t:{unix_time}:t>` : <t:{unix_time}:t>
                `<t:{unix_time}:R>` : <t:{unix_time}:R>"""
            ),
            ephemeral=True,
        )
    except ValueError:
        await ctx.respond(
            "Unable to parse the date and time, please make sure the input is correct and try again.",
            ephemeral=True,
        )
    except Exception:
        logging.exception(
            f'An exception occured with input "{year}-{month}-{day} {hour}:{minute}:{second} {timezone}" (manual mode)'
        )
        await ctx.respond(
            "Unknown exception occured, please try again later.",
            ephemeral=True,
        )


@timestamp.command(
    description="Convert time (in UTC by default) to timestamp, automatic mode"
)
async def automatic(
    ctx,
    user_input: discord.Option(
        str,
        "Work on most formats, D/M/Y format take precedence, relative time is somewhat supported",
        name="datetime",
    ),
    timezone: discord.Option(
        str,
        "±hh:mm, ±hh, ±h:mm, ±h or well-known abbreviations with standard/daylight option (CST/CDT, EST/EDT)",
        default="DEFAULT",
    ),
):
    if timezone == "DEFAULT":
        if ctx.author.id in users_db and "default_timezone" in users_db[ctx.author.id]:
            timezone = users_db[ctx.author.id]["default_timezone"]
        else:
            timezone = "+00:00"
    try:
        (
            tz_name,
            tz_offset_string,
            tz_offset_seconds,
        ) = parsers.parse_timezone_abbreviations(timezone, timezone_abbreviations_data)
    except ValueError:
        try:
            tz_name = ""
            tz_offset_string = timezone
            tz_offset_seconds = parsers.parse_timezone(timezone)
        except ValueError:
            await ctx.respond(
                "Invalid timezone format or unknown abbreviation, please make sure the input is correct and try again.",
                ephemeral=True,
            )
            return

    reference_time = datetime.datetime.utcnow() + relativedelta(
        seconds=tz_offset_seconds
    )
    try:
        ctparsed_time = ctparse.ctparse(user_input, ts=reference_time)
        if ctparsed_time is None:
            await ctx.respond(
                "Unable to parse the date and time, please make sure the input is correct and try again.",
                ephemeral=True,
            )
            return
        ctparsed_resolution = ctparsed_time.resolution
        if type(ctparsed_resolution) == ctparse.types.Time:
            unix_time = round(
                calendar.timegm(
                    datetime.datetime(
                        ctparsed_resolution.year
                        if ctparsed_resolution.year is not None
                        else reference_time.year,
                        ctparsed_resolution.month
                        if ctparsed_resolution.month is not None
                        else reference_time.month,
                        ctparsed_resolution.day
                        if ctparsed_resolution.day is not None
                        else reference_time.day,
                        ctparsed_resolution.hour
                        if ctparsed_resolution.hour is not None
                        else reference_time.hour,
                        ctparsed_resolution.minute
                        if ctparsed_resolution.minute is not None
                        else reference_time.minute,
                    ).timetuple()
                )
            )
            unix_time -= tz_offset_seconds
        elif type(ctparsed_resolution) == ctparse.types.Duration:
            duration_value = ctparsed_resolution.value
            duration_unit = ctparsed_resolution.unit
            if duration_unit == ctparse.types.DurationUnit.MINUTES:
                delta_time = relativedelta(minutes=duration_value)
            elif duration_unit == ctparse.types.DurationUnit.HOURS:
                delta_time = relativedelta(hours=duration_value)
            elif duration_unit == ctparse.types.DurationUnit.DAYS:
                delta_time = relativedelta(days=duration_value)
            elif duration_unit == ctparse.types.DurationUnit.NIGHTS:
                delta_time = relativedelta(days=duration_value)
            elif duration_unit == ctparse.types.DurationUnit.WEEKS:
                delta_time = relativedelta(weeks=duration_value)
            elif duration_unit == ctparse.types.DurationUnit.MONTHS:
                delta_time = relativedelta(months=duration_value)
            elif duration_unit == ctparse.types.DurationUnit.YEARS:
                delta_time = relativedelta(years=duration_value)
            else:
                await ctx.respond(
                    "Duration time unit is not supported, if this is unintentional please verify input and/or switch format used.",
                    ephemeral=True,
                )
                return
            unix_time = round(
                calendar.timegm((datetime.datetime.utcnow() + delta_time).timetuple())
            )
        else:
            await ctx.respond(
                "Interval time is not supported, if this is unintentional please verify input and/or switch format used.",
                ephemeral=True,
            )
            return
        await ctx.respond(
            dedent(
                f"""
                {f"Timezone: {tz_name} ({tz_offset_string})" if tz_name else ""}
                `<t:{unix_time}:F>` : <t:{unix_time}:F>
                `<t:{unix_time}:f>` : <t:{unix_time}:f>
                `<t:{unix_time}:D>` : <t:{unix_time}:D>
                `<t:{unix_time}:d>` : <t:{unix_time}:d>
                `<t:{unix_time}:T>` : <t:{unix_time}:T>
                `<t:{unix_time}:t>` : <t:{unix_time}:t>
                `<t:{unix_time}:R>` : <t:{unix_time}:R>"""
            ),
            ephemeral=True,
        )
    except Exception:
        logging.exception(
            f'An exception occured with input "{user_input} {timezone}" (automatic mode)'
        )
        await ctx.respond(
            "Unknown exception occured, please try again later.",
            ephemeral=True,
        )


config = bot.create_group("config", "Configure the bot", guild_ids=preview_guilds)


@config.command(
    descripton="Setting the default timezone to be used when no timezone argument is provided"
)
async def set_default_timezone(
    ctx,
    new_timezone: discord.Option(
        str,
        "±hh:mm, ±hh, ±h:mm, ±h or well-known abbreviations with standard/daylight option (CST/CDT, EST/EDT)",
    ),
):
    try:
        (
            tz_name,
            tz_offset_string,
            tz_offset_seconds,
        ) = parsers.parse_timezone_abbreviations(
            new_timezone, timezone_abbreviations_data
        )
    except ValueError:
        try:
            tz_name = ""
            tz_offset_string = new_timezone
            tz_offset_seconds = parsers.parse_timezone(new_timezone)
        except ValueError:
            await ctx.respond(
                "Invalid timezone format or unknown abbreviation, please make sure the input is correct and try again.",
                ephemeral=True,
            )
            return

    tz_sign = "+" if tz_offset_seconds >= 0 else "-"
    tz_hour = abs(tz_offset_seconds) // 3600
    tz_minute = (abs(tz_offset_seconds) % 3600) // 60
    tz_string = f"{tz_sign}{tz_hour:02d}:{tz_minute:02d}"

    if ctx.author.id in users_db:
        user_data = users_db[ctx.author.id]
    else:
        user_data = {}
    user_data["default_timezone"] = tz_string
    users_db[ctx.author.id] = user_data
    await ctx.respond(
        f"""Successfully configured default timezone to {f"{tz_name + ' ' if tz_name else ''}{'(' if tz_name else ''}{tz_string}{')' if tz_name else ''}"} for you.""",
        ephemeral=True,
    )
    return


bot.run(os.getenv("TOKEN"))

logging.info("Closing databases")
users_db.close()
logging.info("Databases closed")
logging.info("Exiting...")
