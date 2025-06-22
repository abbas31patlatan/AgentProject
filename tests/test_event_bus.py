import asyncio
from core.event_bus import EventBus


def test_publish_subscribe():
    async def main():
        bus = EventBus()
        result = []

        async def handler(payload):
            result.append(payload)

        await bus.subscribe('test.event', handler)
        await bus.publish('test.event', 42)
        return result

    res = asyncio.run(main())
    assert res == [42]
