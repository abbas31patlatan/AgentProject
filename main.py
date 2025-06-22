# File: main.py

import asyncio
import logging
from core.di import DIContainer, Scope
from core.event_bus import EventBus
from core.memory import MemoryManager
from core.model_manager import ModelManager
from core.api_orchestrator import APIOrchestrator
from core.plugin_loader import PluginLoader
from core.consciousness import ConsciousnessEngine
from core.context_stitcher import ContextStitcher
from gui.qt_app import QtAgentApp

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s] %(name)s: %(message)s"
)

def build_container() -> DIContainer:
    container = DIContainer()
    event_bus = EventBus()
    container.bind(EventBus, lambda: event_bus, scope=Scope.SINGLETON)
    container.bind(MemoryManager, lambda: MemoryManager(), scope=Scope.SINGLETON)
    container.bind(ModelManager, lambda: ModelManager(), scope=Scope.SINGLETON)
    container.bind(APIOrchestrator, lambda: APIOrchestrator(event_bus), scope=Scope.SINGLETON)
    container.bind(PluginLoader, lambda: PluginLoader(event_bus), scope=Scope.SINGLETON)
    container.bind(ContextStitcher, lambda: ContextStitcher(container.get(MemoryManager)), scope=Scope.SINGLETON)
    container.bind(ConsciousnessEngine, lambda: ConsciousnessEngine(
        memory=container.get(MemoryManager),
        model_manager=container.get(ModelManager),
        api_manager=container.get(APIOrchestrator),
        event_bus=container.get(EventBus)
    ), scope=Scope.SINGLETON)
    return container

async def run_engine(container: DIContainer):
    # Bilinci başlat, demo bir mesaj gönder, kapanış yap
    mind = container.get(ConsciousnessEngine)
    await mind.initialize()
    print("AI Başlatıldı. (Çıkmak için Ctrl+C)")
    try:
        while True:
            user_input = input("Sen: ")
            if user_input.strip().lower() in {"exit", "quit", "q"}:
                break
            result = await mind.request(user_input)
            print("AI:", result)
    finally:
        await mind.shutdown()

def run_gui(container: DIContainer):
    mind = container.get(ConsciousnessEngine)
    plugins = container.get(PluginLoader)
    app = QtAgentApp(mind, plugins)
    app.run()

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="AgentProject — Tanrısal AI Asistan")
    parser.add_argument("--cli", action="store_true", help="Sadece terminal arayüzü ile başlat")
    parser.add_argument("--gui", action="store_true", help="GUI başlat (varsayılan)")
    args = parser.parse_args()

    container = build_container()

    if args.cli:
        asyncio.run(run_engine(container))
    else:
        # Bilinci asenkron başlat, GUI’ye aktar
        mind = container.get(ConsciousnessEngine)
        asyncio.get_event_loop().run_until_complete(mind.initialize())
        run_gui(container)
        asyncio.get_event_loop().run_until_complete(mind.shutdown())
