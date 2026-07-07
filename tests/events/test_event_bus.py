from ai_runtime.eventing import EventBus


def test_publish():

    bus = EventBus()

    received = []

    def listener(event):
        received.append(event)

    bus.subscribe(listener)

    bus.publish("hello")

    assert received == ["hello"]


def test_multiple_listeners():

    bus = EventBus()

    a = []
    b = []

    bus.subscribe(a.append)

    bus.subscribe(b.append)

    bus.publish("test")

    assert a == ["test"]

    assert b == ["test"]


def test_unsubscribe():

    bus = EventBus()

    received = []

    listener = received.append

    bus.subscribe(listener)

    bus.unsubscribe(listener)

    bus.publish("hello")

    assert received == []