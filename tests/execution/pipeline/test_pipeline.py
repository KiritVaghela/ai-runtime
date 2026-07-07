from ai_runtime.execution.pipeline import (
    ExecutionPipeline, 
    ExecutionStage
)
from ai_runtime.execution import ExecutionContext
import pytest

class DummyProvider:
    pass


@pytest.mark.asyncio
async def test_empty_pipeline():

    pipeline = ExecutionPipeline()

    context = ExecutionContext(
        provider=DummyProvider(),
    )

    result = await pipeline.execute(context)

    assert result is context



class Stage1(ExecutionStage):

    async def execute(self, context):
        context.metadata["order"] = ["stage1"]
        return context


class Stage2(ExecutionStage):

    async def execute(self, context):
        context.metadata["order"].append("stage2")
        return context


@pytest.mark.asyncio
async def test_stage_order():

    pipeline = ExecutionPipeline()

    pipeline.add(Stage1())
    pipeline.add(Stage2())

    context = ExecutionContext(
        provider=DummyProvider(),
    )

    await pipeline.execute(context)

    assert context.metadata["order"] == [
        "stage1",
        "stage2",
    ]


def test_remove_stage():

    pipeline = ExecutionPipeline()

    stage = object()

    pipeline.add(stage)

    pipeline.remove(stage)

    assert len(pipeline.stages) == 0


def test_clear_pipeline():

    pipeline = ExecutionPipeline()

    pipeline.add(object())
    pipeline.add(object())

    pipeline.clear()

    assert pipeline.stages == []