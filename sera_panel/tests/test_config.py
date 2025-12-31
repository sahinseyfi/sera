import os

os.environ["SERAPANEL_SKIP_INIT"] = "1"

from app_legacy import validate_config


def _base_cfg(relays, dht_gpio=17):
    return {
        "relays": relays,
        "sensors": {
            "dht22_gpio": dht_gpio,
        },
    }


def test_duplicate_gpio_detected():
    cfg = _base_cfg({
        "r1": {"gpio": 5},
        "r2": {"gpio": 5},
    })
    err = validate_config(cfg)
    assert err
    assert "GPIO5" in err
    assert "r1" in err
    assert "r2" in err


def test_reserved_gpio_blocked():
    cfg = _base_cfg({
        "r1": {"gpio": 2},
    })
    err = validate_config(cfg)
    assert err
    assert "GPIO2" in err
    assert "I2C" in err


def test_dht_gpio_conflict():
    cfg = _base_cfg({
        "r1": {"gpio": 17},
    }, dht_gpio=17)
    err = validate_config(cfg)
    assert err
    assert "DHT22 GPIO17" in err
