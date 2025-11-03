from app.db import SessionLocal, engine, Base
from app.models import Strategy

Base.metadata.create_all(bind=engine)
db = SessionLocal()

items = [
    {
        "id": "swing-perp-16h",
        "name": "Swing Perp (16h regime)",
        "description": "1h signals, 16h regime filter",
        "category": "perp",
        "status": "live",
        "markets": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    },
    {
        "id": "mtf-btc-1h-6h-16h",
        "name": "MTF BTC (1h/6h/16h)",
        "description": "1h signals with 6h+16h regimes",
        "category": "perp",
        "status": "live",
        "markets": ["BTCUSDT"],
    },
    {
        "id": "mtf-eth-1h-6h-16h",
        "name": "MTF ETH (1h/6h/16h)",
        "description": "1h signals with 6h+16h regimes",
        "category": "perp",
        "status": "live",
        "markets": ["ETHUSDT"],
    },
    {
        "id": "scalp-perp-15m",
        "name": "Scalp Perp (15m)",
        "description": "15m scalp strategy",
        "category": "perp",
        "status": "live",
        "markets": ["BTCUSDT", "ETHUSDT"],
    },
]

for x in items:
    if not db.get(Strategy, x["id"]):
        db.add(
            Strategy(
                id=x["id"],
                name=x["name"],
                description=x["description"],
                category=x["category"],
                status=x["status"],
                markets=x["markets"],
            )
        )

db.commit()
db.close()
print("Seeded strategies.")