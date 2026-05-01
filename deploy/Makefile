ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)

.PHONY: deploy serve tunnel tail test lint sync-secrets

deploy:
	cd $(ROOT) && modal deploy modal_app/app.py

sync-secrets:
	cd $(ROOT) && .venv/bin/python scripts/sync_modal_secrets.py

serve:
	cd $(ROOT) && uvicorn webhook.server:app --host 0.0.0.0 --port 8080 --reload

tunnel:
	cloudflared tunnel --url http://localhost:8080

tail:
	modal app logs imessage-coding-agent

test:
	cd $(ROOT) && pytest tests/ -v

lint:
	cd $(ROOT) && ruff check . && mypy modal_app/ webhook/ linq/
