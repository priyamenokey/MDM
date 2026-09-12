# Diagrams for Medium Article

This directory contains the diagram source files for the Entity Resolution + Knowledge Graph Medium article.

## Files

1. **architecture-diagram.txt** - Three-layer architecture (ER Engine → Neo4j → Query Layer)
2. **query-flow-diagram.txt** - End-to-end query flow (NL Question → Results)

## How to Use in Medium

### Option 1: Export from Mermaid.live (Recommended)

1. Go to https://mermaid.live
2. Copy the Mermaid markup from the corresponding .txt file
3. Paste into the Mermaid editor
4. Click "Download SVG" or "Download PNG"
5. Upload the image to Medium

### Option 2: Use Excalidraw

1. Go to https://excalidraw.com
2. Recreate the diagram using the flowchart as a guide
3. Export as PNG or SVG
4. Upload to Medium

### Option 3: Screenshot from This Directory

If you have Mermaid CLI installed:
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i diagrams/architecture-diagram.txt -o diagrams/architecture-diagram.png
mmdc -i diagrams/query-flow-diagram.txt -o diagrams/query-flow-diagram.png
```

## Placement in MEDIUM.md

- **Architecture Diagram**: Line ~110, replaces `[Insert image: ER+KG Architecture diagram with three layers]`
- **Query Flow Diagram**: Line ~195, replaces `[Insert image: Query flow diagram]`

## Tips for Medium

- SVG formats better than PNG (scales without pixelation)
- Add alt text to each image: "ER+KG Architecture" and "Query Flow"
- Consider adding captions below each diagram
- If Medium rendering looks off, try PNG instead of SVG

