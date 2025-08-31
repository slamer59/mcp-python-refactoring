#!/usr/bin/env python3
"""
Lancement simple du serveur MCP en mode local
"""

import asyncio
import sys
import os

# Ajouter le répertoire src au path
sys.path.insert(0, 'src')

try:
    from mcp_refactoring_assistant.server import main as server_main, MCP_AVAILABLE
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("💡 Essayez: uv add mcp")
    sys.exit(1)

async def run_server():
    """Lance le serveur MCP"""
    print("🚀 Lancement du serveur MCP Python Refactoring Assistant")
    print("=" * 60)
    print("📡 Serveur en écoute sur stdin/stdout")
    print("💡 Connectez votre client MCP à ce processus")
    print("🔄 Ctrl+C pour arrêter")
    print("=" * 60)
    
    if not MCP_AVAILABLE:
        print("❌ MCP non disponible - mode standalone uniquement")
        print("📁 Pour tester sans MCP: python test_tool.py")
        return
    
    try:
        await server_main()
    except KeyboardInterrupt:
        print("\n👋 Serveur MCP arrêté")
    except Exception as e:
        print(f"❌ Erreur serveur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_server())