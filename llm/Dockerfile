FROM ollama/ollama:0.40.13

ARG MODEL=qwen3:4b-q4_K_M

RUN ollama serve & pid=$!; \
    until ollama list >/dev/null 2>&1; do sleep 1; done; \
    ollama pull ${MODEL}; \
    kill $pid; wait $pid || true

EXPOSE 11434

HEALTHCHECK --interval=10s --timeout=5s --retries=10 \
  CMD ollama list || exit 1
