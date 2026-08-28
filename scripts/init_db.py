import asyncio

from retail_support.checkpointer import get_checkpointer


async def main():
    async with get_checkpointer() as saver:
        await saver.setup()
    print("Checkpoint tables created.")


if __name__ == "__main__":
    asyncio.run(main())
