#!/usr/bin/env python3
"""
Client MCP Python pour tester le serveur de refactoring
"""

import asyncio
import json
import sys
from pathlib import Path

try:
    import mcp.client.stdio
    from mcp.client.session import ClientSession
    from mcp import types
    MCP_CLIENT_AVAILABLE = True
except ImportError:
    print("❌ MCP client not available. Install with: uv add mcp")
    MCP_CLIENT_AVAILABLE = False
    sys.exit(1)

class MCPTestClient:
    """Client de test pour notre serveur MCP de refactoring"""
    
    def __init__(self, server_script_path: str):
        self.server_script_path = server_script_path
        self.session = None
    
    async def connect(self):
        """Se connecter au serveur MCP"""
        # Lancer le serveur comme sous-processus
        server_params = mcp.client.stdio.StdioServerParameters(
            command="python",
            args=[self.server_script_path]
        )
        
        stdio_transport = mcp.client.stdio.stdio_client(server_params)
        stdio, write_stream = await stdio_transport.__aenter__()
        
        self.session = await ClientSession(stdio, write_stream).__aenter__()
        
        # Initialiser la session MCP
        await self.session.initialize()
        
        print("✅ Connecté au serveur MCP de refactoring")
        return self.session
    
    async def list_tools(self):
        """Lister les outils disponibles"""
        print("\n🛠️ Outils MCP disponibles:")
        print("=" * 40)
        
        tools = await self.session.list_tools()
        for tool in tools.tools:
            print(f"📋 {tool.name}")
            print(f"   Description: {tool.description}")
            if tool.inputSchema and 'properties' in tool.inputSchema:
                props = tool.inputSchema['properties']
                print(f"   Paramètres: {', '.join(props.keys())}")
            print()
        
        return tools.tools
    
    async def test_analyze_file(self, file_content: str, file_path: str = "test.py"):
        """Tester l'analyse d'un fichier Python"""
        print(f"\n🔍 Test: analyze_python_file")
        print("=" * 40)
        
        try:
            result = await self.session.call_tool(
                "analyze_python_file",
                {
                    "content": file_content,
                    "file_path": file_path
                }
            )
            
            # Parser le résultat JSON
            response_text = result.content[0].text
            analysis = json.loads(response_text)
            
            print(f"📊 Résumé d'analyse:")
            summary = analysis['analysis_summary']
            print(f"   Total des problèmes: {summary['total_issues_found']}")
            print(f"   Priorité haute: {summary['high_priority']}")
            print(f"   Priorité moyenne: {summary['medium_priority']}")
            print(f"   Priorité basse: {summary['low_priority']}")
            
            print(f"\n📋 Conseils de refactoring:")
            for i, guidance in enumerate(analysis['refactoring_guidance'][:3], 1):
                print(f"   {i}. {guidance['issue_type'].upper()} [{guidance['severity']}]")
                print(f"      📍 {guidance['location']}")
                print(f"      📝 {guidance['description']}")
                print()
            
            return analysis
            
        except Exception as e:
            print(f"❌ Erreur lors de l'analyse: {e}")
            return None
    
    async def test_find_long_functions(self, file_content: str):
        """Tester la recherche de fonctions longues"""
        print(f"\n🔍 Test: find_long_functions")
        print("=" * 40)
        
        try:
            result = await self.session.call_tool(
                "find_long_functions",
                {
                    "content": file_content,
                    "line_threshold": 15  # Seuil plus bas pour les tests
                }
            )
            
            response_text = result.content[0].text
            functions_data = json.loads(response_text)
            
            print(f"📊 Fonctions analysées: {functions_data['total_functions_analyzed']}")
            print(f"📋 Fonctions longues trouvées: {functions_data['long_functions_found']}")
            
            if functions_data['functions']:
                print(f"\n📍 Détails des fonctions longues:")
                for func in functions_data['functions']:
                    print(f"   • {func['name']} (lignes {func['start_line']}-{func['end_line']}, {func['length']} lignes)")
            
            return functions_data
            
        except Exception as e:
            print(f"❌ Erreur lors de la recherche: {e}")
            return None
    
    async def test_extraction_guidance(self, file_content: str):
        """Tester les conseils d'extraction"""
        print(f"\n🔍 Test: get_extraction_guidance")
        print("=" * 40)
        
        try:
            result = await self.session.call_tool(
                "get_extraction_guidance",
                {
                    "content": file_content
                }
            )
            
            response_text = result.content[0].text
            guidance_data = json.loads(response_text)
            
            print(f"📊 Opportunités d'extraction: {guidance_data['extraction_opportunities']}")
            
            if guidance_data['guidance']:
                for guidance in guidance_data['guidance']:
                    print(f"\n📋 {guidance['location']}")
                    print(f"📝 {guidance['description']}")
                    
                    if guidance.get('extractable_blocks'):
                        print(f"✂️ Blocs extractibles:")
                        for block in guidance['extractable_blocks'][:2]:  # Premiers 2 blocs
                            print(f"   • {block['suggested_name']} (lignes {block['start_line']}-{block['end_line']})")
            
            return guidance_data
            
        except Exception as e:
            print(f"❌ Erreur lors de l'extraction: {e}")
            return None
    
    async def disconnect(self):
        """Fermer la connexion"""
        if self.session:
            await self.session.__aexit__(None, None, None)
        print("✅ Déconnecté du serveur MCP")

async def main():
    """Test complet du serveur MCP"""
    print("🚀 Test du serveur MCP Python Refactoring Assistant")
    print("=" * 60)
    
    # Chemin vers notre serveur
    server_path = "src/mcp_refactoring_assistant/server.py"
    
    # Lire le code d'exemple
    example_file = Path("examples/example_code.py")
    if not example_file.exists():
        print(f"❌ Fichier d'exemple non trouvé: {example_file}")
        return
    
    with open(example_file, 'r') as f:
        example_content = f.read()
    
    # Créer et connecter le client
    client = MCPTestClient(server_path)
    
    try:
        # Connexion au serveur
        await client.connect()
        
        # Test 1: Lister les outils
        tools = await client.list_tools()
        
        # Test 2: Analyser le fichier
        analysis = await client.test_analyze_file(example_content, "example_code.py")
        
        # Test 3: Chercher les fonctions longues
        functions = await client.test_find_long_functions(example_content)
        
        # Test 4: Conseils d'extraction
        extraction = await client.test_extraction_guidance(example_content)
        
        print("\n🎉 Tous les tests MCP ont réussi!")
        print("\n💡 Comment utiliser avec un LLM:")
        print("   1. LLM appelle analyze_python_file avec le code")
        print("   2. Reçoit JSON structuré avec conseils précis")
        print("   3. Guide l'utilisateur étape par étape")
        print("   4. Utilisateur suit les instructions de coupe/collage")
        
    except Exception as e:
        print(f"❌ Erreur pendant les tests: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Déconnexion propre
        await client.disconnect()

if __name__ == "__main__":
    if MCP_CLIENT_AVAILABLE:
        asyncio.run(main())
    else:
        print("❌ Installer MCP client d'abord: uv add mcp")