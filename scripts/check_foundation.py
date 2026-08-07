import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT / "packages" / "reliability"))

from reconai_api import app


def main() -> None:
    client = TestClient(app)

    health = client.get("/health")
    health.raise_for_status()
    assert health.json()["status"] == "ok"

    tenant = client.get("/api/v1/demo-tenant")
    tenant.raise_for_status()
    assert tenant.json()["name"] == "Northstar Beverages"

    print("ReconAI foundation API checks OK")


if __name__ == "__main__":
    main()
