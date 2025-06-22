# AgentProject Technical Overview

This document briefly describes the main modules and how they interact.

## Core
- **di.py** – Tiny dependency injection container with thread-safe singleton
  management.
- **event_bus.py** – Async publish/subscribe event system.
- **memory.py** – Persistent sqlite storage for interactions and tasks.
- **model_manager.py** – Discovers GGUF/ONNX/Torch models and loads them on
  demand via a unified `infer` API.
- **api_orchestrator.py** – Handles outbound API calls (REST, gRPC, websockets).
- **plugin_loader.py** – Loads plugins from local or remote sources.
- **context_stitcher.py** – Retrieves relevant context from memory for prompts.
- **consciousness.py** – Central engine orchestrating memory, models and events.
- **refactor_engine.py** – Formats project code when optimization events occur.

## Subsystems
- **action/** – Modules controlling automation, input and robotics.
- **perception/** – Perception layers for audio, vision and other sensors.
- **media/** – Media generation utilities for images, music and video.
- **gui/** – PyQt6 based graphical chat interface.
- **plugin_market/** – Simple client for a remote plugin registry.

All components communicate mainly through the `EventBus`. Dependency injection
via `DIContainer` creates and wires these objects in `main.py`.
