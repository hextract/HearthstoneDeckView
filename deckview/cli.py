import argparse
import asyncio
import importlib
import logging
import os


PLATFORMS = {
    "vk": "deckview.platforms.vk",
    "tg": "deckview.platforms.telegram",
    "ds": "deckview.platforms.discord",
}

ALIASES = {
    "telegram": "tg",
    "discord": "ds",
}


def _normalize_platforms(platforms):
    normalized = [ALIASES.get(platform, platform) for platform in platforms]
    if "all" in normalized:
        return list(PLATFORMS)
    unknown = sorted(set(normalized) - PLATFORMS.keys())
    if unknown:
        raise ValueError(f"Unknown platform: {', '.join(unknown)}")
    return list(dict.fromkeys(normalized))


def _load_runners(platforms):
    runners = []
    for platform in platforms:
        try:
            module = importlib.import_module(PLATFORMS[platform])
        except ModuleNotFoundError as error:
            raise RuntimeError(
                f"The {platform!r} dependencies are not installed. "
                f"Run: uv sync --extra {platform}"
            ) from error
        runners.append((platform, module.run))
    return runners


async def _run(runners):
    if len(runners) == 1:
        await runners[0][1]()
        return

    async with asyncio.TaskGroup() as tasks:
        for platform, runner in runners:
            tasks.create_task(runner(), name=f"deckview-{platform}")


def main(argv=None):
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(prog="deckview")
    parser.add_argument("platforms", nargs="+")
    arguments = parser.parse_args(argv)
    try:
        platforms = _normalize_platforms(arguments.platforms)
        runners = _load_runners(platforms)
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    try:
        asyncio.run(_run(runners))
    except KeyboardInterrupt:
        pass
    except RuntimeError as error:
        logging.getLogger(__name__).error("%s", error)
        raise SystemExit(1) from None
