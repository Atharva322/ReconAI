from fastapi import FastAPI
from fastapi.testclient import TestClient


app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    client = TestClient(app)
    response = client.get("/health")
    response.raise_for_status()
    assert response.json() == {"status": "ok"}
    print("FastAPI toolchain OK")


if __name__ == "__main__":
    main()
