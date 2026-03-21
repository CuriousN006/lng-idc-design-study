from __future__ import annotations

from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import multiprocessing as mp
import os
from typing import TypeVar


T = TypeVar("T")
R = TypeVar("R")


HEAVY_COMMANDS = {
    "run-all",
    "validate",
    "analyze-aux-heat",
    "scenario-study",
    "explore-passive-heat",
    "build-report",
    "build-slides",
    "build-deliverables",
}


@dataclass(slots=True, frozen=True)
class ParallelOptions:
    enabled: bool
    workers: int

    @property
    def is_parallel(self) -> bool:
        return self.enabled and self.workers > 1

    def child_serial(self) -> ParallelOptions:
        return ParallelOptions(enabled=False, workers=1)


def default_worker_count() -> int:
    cpu_count = os.cpu_count() or 1
    return min(6, max(cpu_count - 1, 1))


def default_parallel_enabled_for_command(command: str) -> bool:
    return command in HEAVY_COMMANDS


def resolve_parallel_options(*, enabled: bool, workers: int | None) -> ParallelOptions:
    if not enabled:
        return ParallelOptions(enabled=False, workers=1)
    resolved_workers = default_worker_count() if workers is None else max(int(workers), 1)
    return ParallelOptions(enabled=resolved_workers > 1, workers=resolved_workers)


def map_items(function: Callable[[T], R], items: Iterable[T], options: ParallelOptions) -> list[R]:
    materialized = list(items)
    if not materialized:
        return []
    if not options.is_parallel:
        return [function(item) for item in materialized]

    chunksize = max(1, len(materialized) // (options.workers * 4))
    context = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=options.workers, mp_context=context) as executor:
        return list(executor.map(function, materialized, chunksize=chunksize))
