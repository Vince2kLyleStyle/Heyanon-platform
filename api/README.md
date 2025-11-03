Apply Alembic migrations (from infra directory)

From the `infra/` directory run the following to create and apply migrations inside the running API container. Note: Alembic is included in `api/requirements.txt` so ensure you rebuild the API image if you change requirements.

```powershell
# rebuild api image so alembic is installed
docker compose up -d --build api

# list migrations or create (we added a migration file already)
# generate via autogenerate if you prefer:
# docker compose exec api sh -lc "alembic revision --autogenerate -m 'mychange'"

# apply migrations
docker compose exec api sh -lc "alembic upgrade head"

# rollback last migration (dev only)
docker compose exec api sh -lc "alembic downgrade -1"
```
