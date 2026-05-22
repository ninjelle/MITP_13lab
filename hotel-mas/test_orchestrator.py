import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from orchestrator import HotelOrchestrator

# ── Фикстуры ──────────────────────────────────────────────

@pytest.fixture
def orchestrator():
    orch = HotelOrchestrator()
    orch.nc = AsyncMock()
    return orch


# ── Тесты подключения ─────────────────────────────────────

@pytest.mark.asyncio
async def test_connect():
    orch = HotelOrchestrator()
    mock_nc = AsyncMock()

    with patch("orchestrator.nats.connect", return_value=mock_nc):
        await orch.connect()

    assert orch.nc == mock_nc
    assert mock_nc.subscribe.call_count == 2


# ── Тесты успешного поиска ────────────────────────────────

@pytest.mark.asyncio
async def test_search_rooms_success(orchestrator):
    fake_result = {
        "task_id": "test-123",
        "success": True,
        "rooms": [
            {
                "room_id": "room-102",
                "hotel_name": "Grand Hotel",
                "room_type": "double",
                "capacity": 2,
                "price_per_night": 5500,
                "total_price": 22000,
                "available": True
            }
        ],
        "count": 1
    }

    async def fake_publish(topic, data):
        task = json.loads(data.decode())
        task_id = task["task_id"]
        if task_id in orchestrator.pending:
            orchestrator.pending[task_id].set_result(fake_result)

    orchestrator.nc.publish = fake_publish

    result = await orchestrator.search_rooms(
        city="moscow",
        check_in="2025-09-01",
        check_out="2025-09-05",
        guests=2
    )

    assert result["success"] is True
    assert result["count"] == 1
    assert result["rooms"][0]["room_type"] == "double"


# ── Тесты ошибки от агента ────────────────────────────────

@pytest.mark.asyncio
async def test_search_rooms_agent_error(orchestrator):
    fake_result = {
        "task_id": "test-456",
        "success": False,
        "error": "check_out должен быть позже check_in"
    }

    async def fake_publish(topic, data):
        task = json.loads(data.decode())
        task_id = task["task_id"]
        if task_id in orchestrator.pending:
            orchestrator.pending[task_id].set_result(fake_result)

    orchestrator.nc.publish = fake_publish

    result = await orchestrator.search_rooms(
        city="moscow",
        check_in="2025-09-10",
        check_out="2025-09-05",
        guests=1
    )

    assert result["success"] is False
    assert "check_out" in result["error"]
    assert orchestrator.total_errors == 1


# ── Тесты таймаута ────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_rooms_timeout(orchestrator):
    # publish ничего не делает — агент "молчит"
    orchestrator.nc.publish = AsyncMock()

    with pytest.raises(TimeoutError):
        await orchestrator.search_rooms(
            city="moscow",
            check_in="2025-09-01",
            check_out="2025-09-05",
            guests=1,
            timeout=1,
            max_retries=1
        )

    assert orchestrator.total_timeouts == 1


# ── Тесты retry ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_rooms_retry(orchestrator):
    orchestrator.nc.publish = AsyncMock()

    with pytest.raises(TimeoutError):
        await orchestrator.search_rooms(
            city="moscow",
            check_in="2025-09-01",
            check_out="2025-09-05",
            guests=1,
            timeout=1,
            max_retries=3
        )

    # 3 попытки = 3 вызова publish
    assert orchestrator.nc.publish.call_count == 3
    assert orchestrator.total_timeouts == 3


# ── Тесты метрик ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_metrics_on_success(orchestrator):
    fake_result = {"task_id": "", "success": True, "rooms": [], "count": 0}

    async def fake_publish(topic, data):
        task = json.loads(data.decode())
        fake_result["task_id"] = task["task_id"]
        if task["task_id"] in orchestrator.pending:
            orchestrator.pending[task["task_id"]].set_result(fake_result)

    orchestrator.nc.publish = fake_publish

    await orchestrator.search_rooms(
        city="sochi", check_in="2025-09-01", check_out="2025-09-05", guests=2
    )

    assert orchestrator.total_sent == 1
    assert orchestrator.total_success == 1
    assert orchestrator.total_errors == 0


@pytest.mark.asyncio
async def test_metrics_on_error(orchestrator):
    fake_result = {"task_id": "", "success": False, "error": "ошибка"}

    async def fake_publish(topic, data):
        task = json.loads(data.decode())
        fake_result["task_id"] = task["task_id"]
        if task["task_id"] in orchestrator.pending:
            orchestrator.pending[task["task_id"]].set_result(fake_result)

    orchestrator.nc.publish = fake_publish

    await orchestrator.search_rooms(
        city="moscow", check_in="2025-09-01", check_out="2025-09-05", guests=1
    )

    assert orchestrator.total_sent == 1
    assert orchestrator.total_errors == 1
    assert orchestrator.total_success == 0