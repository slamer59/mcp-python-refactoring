#!/usr/bin/env bun
/**
 * Client de test MCP avec Bun pour le serveur Python Refactoring Assistant
 */

import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { readFileSync } from "fs";

class MCPRefactoringTester {
	constructor() {
		this.client = null;
		this.transport = null;
	}

	async connect() {
		console.log("🚀 Connexion au serveur MCP Python Refactoring Assistant");
		console.log("=".repeat(60));

		// Créer le transport pour communiquer avec le serveur Python
		this.transport = new StdioClientTransport({
			command: "python",
			args: ["simple_mcp_server.py"],
		});

		this.client = new Client(
			{
				name: "refactoring-test-client",
				version: "1.0.0",
			},
			{
				capabilities: {},
			},
		);

		await this.client.connect(this.transport);
		console.log("✅ Connecté au serveur MCP !");
	}

	async listTools() {
		console.log("\n🛠️ Outils MCP disponibles:");
		console.log("=".repeat(40));

		try {
			const response = await this.client.listTools();

			response.tools.forEach((tool, index) => {
				console.log(`📋 ${index + 1}. ${tool.name}`);
				console.log(`   📝 Description: ${tool.description}`);

				if (tool.inputSchema?.properties) {
					const params = Object.keys(tool.inputSchema.properties);
					console.log(`   📥 Paramètres: ${params.join(", ")}`);
				}
				console.log();
			});

			return response.tools;
		} catch (error) {
			console.error("❌ Erreur lors de la liste des outils:", error.message);
			return [];
		}
	}

	async testAnalyzeFile(content, filePath = "test.py") {
		console.log("\n🔍 Test: analyze_python_file");
		console.log("=".repeat(40));

		try {
			const response = await this.client.callTool({
				name: "analyze_python_file",
				arguments: {
					content: content,
					file_path: filePath,
				},
			});

			const result = JSON.parse(response.content[0].text);

			console.log("📊 Résumé d'analyse:");
			const summary = result.analysis_summary;
			console.log(`   • Total des problèmes: ${summary.total_issues_found}`);
			console.log(`   • Priorité critique: ${summary.critical_issues}`);
			console.log(`   • Priorité haute: ${summary.high_priority}`);
			console.log(`   • Priorité moyenne: ${summary.medium_priority}`);
			console.log(`   • Priorité basse: ${summary.low_priority}`);

			console.log("\n📋 Conseils de refactoring:");
			result.refactoring_guidance.slice(0, 3).forEach((guidance, index) => {
				console.log(
					`   ${index + 1}. ${guidance.issue_type.toUpperCase()} [${guidance.severity}]`,
				);
				console.log(`      📍 ${guidance.location}`);
				console.log(`      📝 ${guidance.description}`);

				if (
					guidance.extractable_blocks &&
					guidance.extractable_blocks.length > 0
				) {
					console.log(
						`      ✂️  ${guidance.extractable_blocks.length} blocs extractibles`,
					);
				}
				console.log();
			});

			console.log(
				"🔧 Outils utilisés:",
				Object.entries(result.tools_used)
					.filter(([_, used]) => used)
					.map(([tool, _]) => tool)
					.join(", "),
			);

			return result;
		} catch (error) {
			console.error("❌ Erreur lors de l'analyse:", error.message);
			return null;
		}
	}

	async testFindLongFunctions(content) {
		console.log("\n🔍 Test: find_long_functions");
		console.log("=".repeat(40));

		try {
			const response = await this.client.callTool({
				name: "find_long_functions",
				arguments: {
					content: content,
					line_threshold: 15, // Seuil plus bas pour voir des résultats
				},
			});

			const result = JSON.parse(response.content[0].text);

			console.log(`📊 Fonctions analysées: ${result.total_functions_analyzed}`);
			console.log(
				`📋 Fonctions longues trouvées: ${result.long_functions_found}`,
			);

			if (result.functions && result.functions.length > 0) {
				console.log("\n📍 Détails des fonctions longues:");
				result.functions.forEach((func) => {
					console.log(
						`   • ${func.name} (lignes ${func.start_line}-${func.end_line}, ${func.length} lignes)`,
					);
				});
			} else {
				console.log("   💡 Aucune fonction longue détectée (seuil: 15 lignes)");
			}

			return result;
		} catch (error) {
			console.error("❌ Erreur lors de la recherche:", error.message);
			return null;
		}
	}

	async testExtractionGuidance(content) {
		console.log("\n🔍 Test: get_extraction_guidance");
		console.log("=".repeat(40));

		try {
			const response = await this.client.callTool({
				name: "get_extraction_guidance",
				arguments: {
					content: content,
				},
			});

			const result = JSON.parse(response.content[0].text);

			console.log(
				`📊 Opportunités d'extraction: ${result.extraction_opportunities}`,
			);

			if (result.guidance && result.guidance.length > 0) {
				result.guidance.forEach((guidance, index) => {
					console.log(`\n📋 ${index + 1}. ${guidance.location}`);
					console.log(`📝 ${guidance.description}`);

					if (guidance.extractable_blocks) {
						console.log("✂️ Blocs extractibles:");
						guidance.extractable_blocks.slice(0, 2).forEach((block) => {
							console.log(
								`   • ${block.suggested_name} (lignes ${block.start_line}-${block.end_line})`,
							);
							console.log(
								`     📥 Paramètres: ${block.variables_used.join(", ") || "Aucun"}`,
							);
							console.log(
								`     📤 Variables modifiées: ${block.variables_modified.join(", ") || "Aucune"}`,
							);
						});
					}

					// Montrer quelques étapes d'extraction
					if (guidance.precise_steps && guidance.precise_steps.length > 0) {
						console.log("📋 Étapes d'extraction (extrait):");
						guidance.precise_steps.slice(0, 5).forEach((step) => {
							console.log(`     ${step}`);
						});
						if (guidance.precise_steps.length > 5) {
							console.log(
								`     ... et ${guidance.precise_steps.length - 5} étapes supplémentaires`,
							);
						}
					}
				});
			} else {
				console.log("   💡 Aucune opportunité d'extraction détectée");
			}

			return result;
		} catch (error) {
			console.error("❌ Erreur lors de l'extraction:", error.message);
			return null;
		}
	}

	async disconnect() {
		if (this.client) {
			await this.client.close();
		}
		console.log("\n👋 Déconnecté du serveur MCP");
	}
}

async function main() {
	console.log("🧪 Test du serveur MCP Python Refactoring Assistant avec Bun");
	console.log("=".repeat(70));

	// Lire le fichier d'exemple
	let exampleContent;
	try {
		exampleContent = readFileSync("examples/example_code.py", "utf8");
	} catch (error) {
		console.error(
			"❌ Impossible de lire examples/example_code.py:",
			error.message,
		);
		process.exit(1);
	}

	const tester = new MCPRefactoringTester();

	try {
		// Connexion
		await tester.connect();

		// Test 1: Lister les outils
		const tools = await tester.listTools();

		// Test 2: Analyser le fichier complet
		const analysis = await tester.testAnalyzeFile(
			exampleContent,
			"example_code.py",
		);

		// Test 3: Chercher les fonctions longues
		const longFunctions = await tester.testFindLongFunctions(exampleContent);

		// Test 4: Conseils d'extraction
		const extractionGuidance =
			await tester.testExtractionGuidance(exampleContent);

		// Résumé final
		console.log("\n🎉 Tests MCP terminés avec succès !");
		console.log("=".repeat(50));
		console.log("💡 Comment un LLM utiliserait ce serveur MCP :");
		console.log("   1. 🤖 LLM appelle analyze_python_file avec le code");
		console.log("   2. 📊 Reçoit JSON structuré avec conseils précis");
		console.log("   3. 👨‍💻 Guide l'utilisateur étape par étape");
		console.log("   4. ✂️ Utilisateur suit les instructions de coupe/collage");
		console.log("   5. ✅ Code refactorisé sans modification automatique !");
	} catch (error) {
		console.error("❌ Erreur pendant les tests:", error);
	} finally {
		await tester.disconnect();
	}
}

// Lancement du test
main().catch(console.error);
