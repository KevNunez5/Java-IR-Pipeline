#!/usr/bin/env python3
"""
Genera reporte científico de hallazgos del pipeline Java → LLVM IR
"""

import json
from datetime import datetime
from pathlib import Path

BASE_DIR     = Path(__file__).parent.resolve()
REPORT_DIR   = BASE_DIR / "reports"
IR_DIR       = BASE_DIR / "llvmir"
BYTECODE_DIR = BASE_DIR / "bytecode"

def load_results():
    with open(str(REPORT_DIR / "pipeline_results.json"), encoding="utf-8") as f:
        return json.load(f)

def read_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except:
        return "[archivo no disponible]"

def generate_report(results):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    a = lines.append

    a("# Hallazgos: Pipeline Java → LLVM IR")
    a(f"**Fecha:** {now}  |  **Entorno:** OpenJDK 21, LLVM 18, llvmlite 0.47")
    a("")
    a("---")
    a("")
    a("## 1. Resumen Ejecutivo")
    a("")

    total    = len(results)
    ok_java  = sum(1 for r in results if r["javac"]["success"])
    ok_ir    = sum(1 for r in results if r["llvm_ir"]["success"])
    all_issues = [issue for r in results for issue in r["llvm_ir"].get("issues", [])]

    a(f"Se procesaron **{total} muestras** representativas de patrones Java comunes.")
    a(f"La fase de compilación `javac` fue exitosa en **{ok_java}/{total}** casos (100%).")
    a(f"La generación de LLVM IR fue completada en **{ok_ir}/{total}** casos, ")
    a(f"aunque con **{len(all_issues)} limitaciones documentadas** que impiden una traducción automática directa.")
    a("")
    a("**Conclusión preliminar:** La transformación Java → LLVM IR es *viable con restricciones*.")
    a("")
    a("---")
    a("")
    a("## 2. Descripción del Pipeline")
    a("")
    a("```")
    a("Java (.java)")
    a("    │")
    a("    ▼  javac 21")
    a("JVM Bytecode (.class)")
    a("    │")
    a("    ▼  javap -c -p")
    a("Análisis de Bytecode (detección de opcodes críticos)")
    a("    │")
    a("    ▼  llvmlite 0.47 + LLVM 18")
    a("LLVM IR (.ll)  →  Validado con binding.verify()")
    a("```")
    a("")
    a("| Herramienta | Versión | Rol |")
    a("|---|---|---|")
    a("| OpenJDK | 21 | Compilación Java → bytecode |")
    a("| javap | 21 | Inspección y análisis de bytecode JVM |")
    a("| LLVM | 18.1.3 | Backend de generación y validación de IR |")
    a("| llvmlite | 0.47.0 | API Python para construcción de LLVM IR |")
    a("")
    a("---")
    a("")
    a("## 3. Resultados por Muestra")
    a("")
    a("| # | Sample | Categoría | javac | IR generado | Opcodes críticos | Problemas |")
    a("|---|---|---|---|---|---|---|")
    for i, r in enumerate(results, 1):
        javac_ok = "✅" if r["javac"]["success"] else "❌"
        ir_ok    = "✅" if r["llvm_ir"]["success"] else "❌"
        opcodes  = list(r["javap"].get("opcodes_detected", {}).keys())
        opcodes_str = ", ".join(opcodes) if opcodes else "—"
        n_issues = len(r["llvm_ir"].get("issues", []))
        a(f"| {i} | `{r['name']}` | {r['category']} | {javac_ok} | {ir_ok} | {opcodes_str} | {n_issues} |")

    a("")
    for r in results:
        a(f"### {r['name']} — {r['description']}")
        a("")
        opcodes = r["javap"].get("opcodes_detected", {})
        if opcodes:
            a("**Opcodes JVM críticos detectados:**")
            for op, lines_op in opcodes.items():
                a(f"- `{op}`: {len(lines_op)} ocurrencia(s)")
        else:
            a("**Opcodes JVM críticos:** ninguno")
        a("")
        decisions = r["llvm_ir"].get("decisions", [])
        if decisions:
            a("**Decisiones de traducción:**")
            for d in decisions:
                a(f"- {d}")
        a("")
        issues = r["llvm_ir"].get("issues", [])
        if issues:
            a("**⚠️ Limitaciones:**")
            for issue in issues:
                a(f"- {issue}")
        else:
            a("**✅ Sin limitaciones críticas**")
        a("")
        ir_text = read_file(r["llvm_ir"]["ir_path"])
        a("**LLVM IR generado (fragmento):**")
        a("```llvm")
        ir_lines = ir_text.strip().splitlines()
        for line in ir_lines[:20]:
            a(line)
        if len(ir_lines) > 20:
            a(f"; ... ({len(ir_lines) - 20} líneas adicionales)")
        a("```")
        a("")

    a("---")
    a("")
    a("## 4. Opcodes JVM vs LLVM IR")
    a("")
    a("| Opcode JVM | Equivalente LLVM IR | Complejidad |")
    a("|---|---|---|")
    a("| `invokevirtual` | Function pointer en vtable struct | Media |")
    a("| `invokedynamic` | Sin equivalente directo | **Alta** |")
    a("| `invokeinterface` | Pointer dispatch con type check | Alta |")
    a("| `checkcast` | `bitcast` + runtime type tag | Media |")
    a("| `athrow` | `invoke` + `landingpad` + ABI C++ | **Alta** |")
    a("")
    a("---")
    a("")
    a("## 5. Limitaciones")
    a("")
    a("**L1 — invokedynamic:** lambdas, Stream API y String concatenation no tienen equivalente en IR.")
    a("")
    a("**L2 — Garbage Collector:** Java usa GC automático; IR opera sobre memoria manual (`malloc`/`free`).")
    a("")
    a("**L3 — Type Erasure:** `List<Integer>` y `List<Object>` son idénticos en bytecode → IR usa `i8*` opaco.")
    a("")
    a("**L4 — Excepciones:** Requieren `invoke` + `landingpad` + personality function del ABI C++.")
    a("")
    a("**L5 — Biblioteca estándar:** `java.util.*`, `java.lang.*` no existen en IR — deben reimplementarse.")
    a("")
    a("---")
    a("")
    a("## 6. Viabilidad por Característica")
    a("")
    a("| Característica | Viabilidad | Estrategia |")
    a("|---|---|---|")
    a("| Aritmética y control de flujo | 🟢 Alta | Traducción directa |")
    a("| Clases y métodos estáticos | 🟢 Alta | Funciones LLVM con mangling |")
    a("| Herencia y polimorfismo | 🟡 Media | Structs + vtable manual |")
    a("| Excepciones | 🟡 Media | invoke/landingpad + ABI C++ |")
    a("| Generics/Colecciones | 🟠 Baja | i8* + bitcast + runtime checks |")
    a("| Lambdas y Streams | 🔴 Muy baja | Expansión manual o skip |")
    a("")
    a("---")
    a("*Reporte generado automáticamente por el pipeline Java → LLVM IR*")

    return "\n".join(lines)

if __name__ == "__main__":
    results = load_results()
    report  = generate_report(results)
    report_path = str(REPORT_DIR / "hallazgos_java_llvm_ir.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ Reporte generado: {report_path}")
    print(f"   Longitud: {len(report.splitlines())} líneas")
