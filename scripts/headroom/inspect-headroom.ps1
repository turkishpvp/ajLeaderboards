param(
    [int]$RecentLogs = 10,
    [string]$ExportGraphPath = "",
    [string]$WorkspaceDir = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $WorkspaceDir) { $WorkspaceDir = Join-Path $repoRoot ".headroom" }

$memoryDb = Join-Path $WorkspaceDir "memory.db"
$graphDb = Join-Path $WorkspaceDir "memory_graph.db"
$sharedContextPath = Join-Path $WorkspaceDir "shared-context.json"
$logFile = Join-Path $WorkspaceDir "logs\proxy.jsonl"

if (-not (Test-Path $memoryDb)) { throw "Headroom memory DB not found at $memoryDb" }
if (-not (Test-Path $graphDb)) { throw "Headroom graph DB not found at $graphDb" }

$python = @'
import json
import sqlite3
import sys
from pathlib import Path

memory_db = sys.argv[1]
graph_db = sys.argv[2]
shared_context_path = Path(sys.argv[3])
export_path = sys.argv[4] if len(sys.argv) > 4 else ""

def fetch_rows(con, sql):
    con.row_factory = sqlite3.Row
    return [dict(row) for row in con.execute(sql)]

summary = {}
memory_con = sqlite3.connect(memory_db)
graph_con = sqlite3.connect(graph_db)
summary["memories"] = memory_con.execute("select count(*) from memories").fetchone()[0]
summary["memory_categories"] = fetch_rows(memory_con, "select category, count(*) as count from memories group by category order by count desc, category asc")
summary["entities"] = graph_con.execute("select count(*) from entities").fetchone()[0]
summary["relationships"] = graph_con.execute("select count(*) from relationships").fetchone()[0]
summary["recent_entities"] = fetch_rows(graph_con, "select id, name, entity_type, description, updated_at from entities order by updated_at desc limit 25")
summary["recent_relationships"] = fetch_rows(graph_con, "select id, source_id, target_id, relation_type, created_at from relationships order by created_at desc limit 25")
shared_context = {"entries": 0, "keys": [], "total_original_tokens": 0, "total_compressed_tokens": 0, "savings_percent": 0.0}
if shared_context_path.exists():
    payload = json.loads(shared_context_path.read_text(encoding="utf-8"))
    items = payload.get("entries", {})
    shared_context["entries"] = len(items)
    shared_context["keys"] = sorted(items.keys())
    total_original = sum(item.get("original_tokens", 0) for item in items.values())
    total_compressed = sum(item.get("compressed_tokens", 0) for item in items.values())
    shared_context["total_original_tokens"] = total_original
    shared_context["total_compressed_tokens"] = total_compressed
    if total_original > 0:
        shared_context["savings_percent"] = round((1 - total_compressed / total_original) * 100, 1)
summary["shared_context"] = shared_context
print(json.dumps(summary, ensure_ascii=True, indent=2))
if export_path:
    with open(export_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
memory_con.close()
graph_con.close()
'@

$python | & python - $memoryDb $graphDb $sharedContextPath $ExportGraphPath
if (Test-Path $logFile) {
    Write-Host ""
    Write-Host "Recent proxy log lines:"
    Get-Content $logFile -Tail $RecentLogs
}
