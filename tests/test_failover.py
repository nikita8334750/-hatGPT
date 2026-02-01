from app.services.provider_manager import ProviderManager


class FakeProvider:
    def __init__(self, name: str):
        self.name = name


def test_failover_trips_after_failures():
    primary = FakeProvider("primary")
    fallback = FakeProvider("fallback")
    manager = ProviderManager(primary, fallback)
    for _ in range(5):
        manager.record_failure()
    assert manager.active_provider().name == "fallback"
