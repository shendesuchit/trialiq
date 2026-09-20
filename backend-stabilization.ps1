Set-Location F:\trialiq

$CleanPython = "C:\Users\Admin\AppData\Local\Temp\trialiq-clean-install\venv\Scripts\python.exe"

@'
from trialiq.config.settings import Settings

settings = Settings()

print("Settings loaded successfully")
print("Neo4j URI configured:", bool(settings.neo4j_uri))
print("Neo4j username configured:", bool(settings.neo4j_username))
print("Neo4j password configured:", bool(settings.neo4j_password))
print("Neo4j database:", settings.neo4j_database)
print("PostgreSQL username configured:", bool(settings.postgres_username))
print("PostgreSQL password configured:", bool(settings.postgres_password))
print("LLM provider:", settings.llm_provider)

required = {
    "NEO4J_URI": settings.neo4j_uri,
    "NEO4J_USERNAME": settings.neo4j_username,
    "NEO4J_PASSWORD": settings.neo4j_password,
    "POSTGRES_USERNAME": settings.postgres_username,
    "POSTGRES_PASSWORD": settings.postgres_password,
}

missing = [name for name, value in required.items() if not value]

if missing:
    raise RuntimeError("Missing required configuration fields: " + ", ".join(missing))

print("PASS configuration validation")
'@ | & $CleanPython -