import json

filepath = "nbs/00_core.ipynb"
with open(filepath, "r") as f:
    data = json.load(f)

for cell in data.get("cells", []):
    if cell.get("cell_type") == "code":
        sources = cell.get("source", [])
        new_sources = []
        for line in sources:
            if line == "    import time\n" or line == "    import time":
                continue
            new_sources.append(line)
        cell["source"] = new_sources

with open(filepath, "w") as f:
    json.dump(data, f, indent=1)
