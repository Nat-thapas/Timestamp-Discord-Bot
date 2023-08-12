import calendar
import datetime
import os
import re
from textwrap import dedent

import ctparse
import discord
import dotenv
from dateutil.relativedelta import relativedelta

dotenv.load_dotenv()

bot = discord.Bot()


@bot.event
async def on_ready():
    print(f"{bot.user} is now ready.")


timestamp = bot.create_group(
    "timestamp", "Convert time to timestamp"#, guild_ids=[772410370810839070]  # Uncomment to get instant propagation of slash commands
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
        "±hh:mm or ±hh, leading zero in the hours part can be omitted",
        default="+00:00",
    ),
):
    if 0 <= year < 100:
        current_year = datetime.datetime.utcnow().year
        current_modifier = round(current_year, -2)
        past_modifier = current_modifier - 100
        future_modifier = current_modifier + 100
        current_full_year = current_modifier + year
        past_full_year = past_modifier + year
        future_full_year = future_modifier + year
        if abs(current_year - current_full_year) <= abs(current_year - past_full_year):
            if abs(current_year - current_full_year) < abs(
                current_year - future_full_year
            ):
                year = current_full_year
            else:
                year = future_full_year
        else:
            if abs(current_year - past_full_year) < abs(
                current_year - future_full_year
            ):
                year = past_full_year
            else:
                year = future_full_year
    tz_match = re.search("([+-])(\d?\d)(?::([0-5]\d))?", timezone)
    if not tz_match:
        await ctx.respond(
            "Invalid timezone format, please make sure the input is correct and try again.",
            ephemeral=True,
        )
        return
    tz_sign = 1 if tz_match[1] == "+" else -1
    tz_hour = int(tz_match[2])
    tz_minute = int(tz_match[3]) if tz_match[3] else 0
    tz_offset_seconds = tz_sign * 60 * (tz_hour * 60 + tz_minute)
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
        "Work on most formats, D/M/Y format take precedence, TZ in this input is likely to be ignored",
        name="datetime",
    ),
    timezone: discord.Option(
        str,
        "±hh:mm or ±hh, leading zero in the hours part can be omitted",
        default="+00:00",
    ),
):
    tz_match = re.search("([+-])(\d?\d)(?::([0-5]\d))?", timezone)
    if not tz_match:
        await ctx.respond(
            "Invalid timezone format, please make sure the input is correct and try again.",
            ephemeral=True,
        )
        return
    tz_sign = 1 if tz_match[1] == "+" else -1
    tz_hour = int(tz_match[2])
    tz_minute = int(tz_match[3]) if tz_match[3] else 0
    tz_offset_seconds = tz_sign * 60 * (tz_hour * 60 + tz_minute)
    try:
        ctparsed_time = ctparse.ctparse(user_input, ts=datetime.datetime.utcnow())
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
                        else datetime.datetime.utcnow().year,
                        ctparsed_resolution.month
                        if ctparsed_resolution.month is not None
                        else datetime.datetime.utcnow().month,
                        ctparsed_resolution.day
                        if ctparsed_resolution.day is not None
                        else datetime.datetime.utcnow().day,
                        ctparsed_resolution.hour
                        if ctparsed_resolution.hour is not None
                        else datetime.datetime.utcnow().hour,
                        ctparsed_resolution.minute
                        if ctparsed_resolution.minute is not None
                        else datetime.datetime.utcnow().minute,
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
        await ctx.respond(
            "Unknown exception occured, please try again later.",
            ephemeral=True,
        )


bot.run(os.getenv("TOKEN"))
