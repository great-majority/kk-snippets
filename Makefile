.PHONY: run format init

run:
	uv run streamlit run streamlit_app.py

format:
	uv run ruff check --select I --fix .
	uv run ruff format .

init:
	uv sync
