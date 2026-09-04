#!/bin/sh
# Install markdrop + extras for the web image. Used by the Dockerfile.
# MARKDROP_ENGINE=full|lite
# MARKDROP_EXTRAS=comma-separated extras (lite,anthropic,groq,litellm,local-models)
set -eu

ENGINE="${MARKDROP_ENGINE:-full}"
EXTRAS="${MARKDROP_EXTRAS:-lite,litellm}"

install_extra_packages() {
  old_ifs=$IFS
  IFS=,
  for extra in $EXTRAS; do
    extra=$(printf "%s" "$extra" | tr -d " ")
    case "$extra" in
      "") ;;
      lite) pip install --no-cache-dir pymupdf4llm ;;
      anthropic) pip install --no-cache-dir "anthropic>=0.40.0" ;;
      groq) pip install --no-cache-dir "groq>=0.14.0" ;;
      litellm) pip install --no-cache-dir "litellm>=1.0.0" ;;
      local-models) pip install --no-cache-dir ollama ;;
      all)
        pip install --no-cache-dir pymupdf4llm "anthropic>=0.40.0" "groq>=0.14.0" "litellm>=1.0.0" ollama
        ;;
      *)
        echo "Unknown extra: $extra" >&2
        exit 1
        ;;
    esac
  done
  IFS=$old_ifs
}

if [ "$ENGINE" = "lite" ]; then
  pip install --no-cache-dir --no-deps .
  pip install --no-cache-dir -r web/requirements-engine-lite.txt
  install_extra_packages
else
  # CPU wheels for both. Docling pulls torchvision from PyPI (CUDA build);
  # pairing that with CPU torch raises: operator torchvision::nms does not exist.
  pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
  extras_trimmed=$(printf "%s" "$EXTRAS" | tr -d " ")
  if [ -n "$extras_trimmed" ]; then
    pip install --no-cache-dir ".[${extras_trimmed}]"
  else
    pip install --no-cache-dir .
  fi
  pip install --no-cache-dir --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi
