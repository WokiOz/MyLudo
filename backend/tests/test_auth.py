def test_health_is_public(make_client):
    client = make_client("secret")
    assert client.get("/api/health").json() == {"status": "ok"}


def test_without_password_everything_is_open(client):
    assert client.get("/api/auth/status").json() == {"auth_required": False, "authenticated": True}
    assert client.get("/api/games").status_code == 200


def test_password_protects_the_api(make_client):
    client = make_client("secret")
    assert client.get("/api/games").status_code == 401
    assert client.get("/api/export/games.csv").status_code == 401
    assert client.get("/api/status").status_code == 401
    assert client.get("/api/auth/status").json() == {"auth_required": True, "authenticated": False}

    assert client.post("/api/auth/login", json={"password": "faux"}).status_code == 401
    assert client.post("/api/auth/login", json={"password": "secret"}).status_code == 200
    assert client.get("/api/games").status_code == 200

    client.post("/api/auth/logout")
    assert client.get("/api/games").status_code == 401


def test_forged_cookie_is_refused(make_client):
    client = make_client("secret")
    client.cookies.set("myludo_session", "9999999999.deadbeef")
    assert client.get("/api/games").status_code == 401


def test_cookie_is_invalid_after_password_change(make_client):
    client = make_client("secret")
    client.post("/api/auth/login", json={"password": "secret"})
    token = client.cookies.get("myludo_session")
    other = make_client("autre")
    other.cookies.set("myludo_session", token)
    assert other.get("/api/games").status_code == 401


def test_too_many_failures_lock_the_login(make_client):
    client = make_client("secret")
    for _ in range(5):
        assert client.post("/api/auth/login", json={"password": "x"}).status_code == 401
    assert client.post("/api/auth/login", json={"password": "secret"}).status_code == 429
