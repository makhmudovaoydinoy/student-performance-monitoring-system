#!/usr/bin/env bash
# PlantUML -> PNG va SVG.  Variantlar:
#  1) Docker:   ./render.sh
#  2) Lokal:    plantuml -tpng *.puml  (java + graphviz kerak)
#  3) Onlayn:   https://www.plantuml.com/plantuml  (kodni joylab, PNG/SVG yuklab oling)
#  4) VS Code:  "PlantUML" kengaytmasi -> Export Current Diagram
set -e
cd "$(dirname "$0")"
docker run --rm -v "$PWD:/data" -w /data plantuml/plantuml -tpng "*.puml"
docker run --rm -v "$PWD:/data" -w /data plantuml/plantuml -tsvg "*.puml"
echo "Tayyor: PNG va SVG fayllar shu papkada."
