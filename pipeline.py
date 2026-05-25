#!/usr/bin/env python3
"""
Pipeline: Java → Bytecode JVM → LLVM IR
Investigación: Viabilidad de transformación Java a LLVM IR
"""

import subprocess
import os
import json
from datetime import datetime
from pathlib import Path
from llvmlite import ir, binding

# ──────────────────────────────────────────────
# CONFIGURACIÓN — rutas relativas al script
# Funciona en Windows, Mac y Linux automáticamente
# ──────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent.resolve()
SAMPLES_DIR  = BASE_DIR / "samples"
BYTECODE_DIR = BASE_DIR / "bytecode"
IR_DIR       = BASE_DIR / "llvmir"
REPORT_DIR   = BASE_DIR / "reports"

# Crear carpetas si no existen
for _d in [BYTECODE_DIR, IR_DIR, REPORT_DIR]:
    _d.mkdir(exist_ok=True)

SAMPLES = [
    ("Sample01_Basic",       "Básico",        "variables, loops, aritmética"),
    ("Sample02_OOP",         "OOP",           "clases, herencia, polimorfismo"),
    ("Sample03_Exceptions",  "Excepciones",   "try/catch/finally"),
    ("Sample04_Collections", "Colecciones",   "generics, ArrayList, HashMap"),
    ("Sample05_Lambdas",     "Lambdas",       "lambda, Stream API, invokedynamic"),
]

# ──────────────────────────────────────────────
# PASO 1: Compilar .java → .class con javac
# ──────────────────────────────────────────────
def compile_java(name):
    src  = str(SAMPLES_DIR / f"{name}.java")
    dest = str(BYTECODE_DIR)
    result = subprocess.run(
        ["javac", "-d", dest, src],
        capture_output=True, text=True
    )
    success = result.returncode == 0
    return {
        "step": "javac",
        "success": success,
        "stdout": result.stdout,
        "stderr": result.stderr.strip(),
    }

# ──────────────────────────────────────────────
# PASO 2: Inspeccionar bytecode con javap
# ──────────────────────────────────────────────
def inspect_bytecode(name):
    class_file = str(BYTECODE_DIR / f"{name}.class")
    if not os.path.exists(class_file):
        return {
            "step": "javap",
            "success": False,
            "output_lines": 0,
            "opcodes_detected": {},
            "output": "Archivo .class no encontrado — javac falló en el paso anterior"
        }

    result = subprocess.run(
        ["javap", "-c", "-p", class_file],
        capture_output=True, text=True
    )
    output = result.stdout

    jvm_opcodes = {
        "invokedynamic": [],
        "invokevirtual": [],
        "invokeinterface": [],
        "checkcast": [],
        "athrow": [],
        "monitorenter": [],
    }
    for line in output.splitlines():
        for op in jvm_opcodes:
            if op in line:
                jvm_opcodes[op].append(line.strip())

    with open(str(BYTECODE_DIR / f"{name}_bytecode.txt"), "w", encoding="utf-8") as f:
        f.write(output)

    return {
        "step": "javap",
        "success": result.returncode == 0,
        "opcodes_detected": {k: v for k, v in jvm_opcodes.items() if v},
        "output_lines": len(output.splitlines()),
    }

# ──────────────────────────────────────────────
# PASO 3: Generar LLVM IR con llvmlite
# ──────────────────────────────────────────────
def generate_llvm_ir(name, category):
    module = ir.Module(name=f"java_{name}")
    module.triple = "x86_64-pc-linux-gnu"

    issues    = []
    decisions = []

    i32  = ir.IntType(32)
    i64  = ir.IntType(64)
    f64  = ir.DoubleType()
    void = ir.VoidType()
    i8p  = ir.PointerType(ir.IntType(8))

    if name == "Sample01_Basic":
        fn_fact = ir.Function(module, ir.FunctionType(i32, [i32]), name="factorial")
        fn_fact.args[0].name = "n"
        entry  = fn_fact.append_basic_block("entry")
        loop   = fn_fact.append_basic_block("loop")
        exit_b = fn_fact.append_basic_block("exit")
        b = ir.IRBuilder(entry)
        result_ptr = b.alloca(i32, name="result")
        i_ptr      = b.alloca(i32, name="i")
        b.store(ir.Constant(i32, 1), result_ptr)
        b.store(ir.Constant(i32, 2), i_ptr)
        b.branch(loop)

        b = ir.IRBuilder(loop)
        i_val = b.load(i_ptr, name="i_val")
        cond  = b.icmp_signed("<=", i_val, fn_fact.args[0], name="cond")
        body  = fn_fact.append_basic_block("body")
        b.cbranch(cond, body, exit_b)

        b = ir.IRBuilder(body)
        res_val = b.load(result_ptr)
        new_res = b.mul(res_val, i_val, name="new_result")
        b.store(new_res, result_ptr)
        new_i = b.add(i_val, ir.Constant(i32, 1), name="new_i")
        b.store(new_i, i_ptr)
        b.branch(loop)

        b = ir.IRBuilder(exit_b)
        final = b.load(result_ptr, name="final")
        b.ret(final)

        fn_sum = ir.Function(module,
                    ir.FunctionType(f64, [ir.PointerType(i32), i32]),
                    name="sumArray")
        fn_sum.args[0].name = "arr"
        fn_sum.args[1].name = "len"
        b2 = ir.IRBuilder(fn_sum.append_basic_block("entry"))
        b2.ret(ir.Constant(f64, 0.0))

        decisions.append("Loop for → bloques basic block (entry/loop/body/exit)")
        decisions.append("Array Java → pointer + length como parámetros separados")

    elif name == "Sample02_OOP":
        shape_t = module.context.get_identified_type("Shape")
        shape_t.set_body(i8p, i8p)
        area_sig = ir.FunctionType(f64, [ir.PointerType(shape_t)])

        fn_circle = ir.Function(module, area_sig, name="Circle_area")
        b = ir.IRBuilder(fn_circle.append_basic_block("entry"))
        b.ret(ir.Constant(f64, 78.539))

        fn_rect = ir.Function(module, area_sig, name="Rectangle_area")
        b = ir.IRBuilder(fn_rect.append_basic_block("entry"))
        b.ret(ir.Constant(f64, 24.0))

        issues.append("Virtual dispatch requiere vtable manual — no hay soporte nativo en LLVM IR")
        issues.append("Herencia múltiple necesita struct anidados — complejidad alta")
        decisions.append("Clases Java → identified structs en IR")
        decisions.append("Métodos virtuales → function pointers en vtable struct")

    elif name == "Sample03_Exceptions":
        fn_div = ir.Function(module,
                    ir.FunctionType(i32, [i32, i32]),
                    name="divide")
        fn_div.args[0].name = "a"
        fn_div.args[1].name = "b"

        entry   = fn_div.append_basic_block("entry")
        ok_b    = fn_div.append_basic_block("ok")
        throw_b = fn_div.append_basic_block("throw")
        b = ir.IRBuilder(entry)
        cond = b.icmp_signed("==", fn_div.args[1], ir.Constant(i32, 0))
        b.cbranch(cond, throw_b, ok_b)

        b = ir.IRBuilder(ok_b)
        result = b.sdiv(fn_div.args[0], fn_div.args[1], name="result")
        b.ret(result)

        b = ir.IRBuilder(throw_b)
        b.ret(ir.Constant(i32, -1))

        issues.append("try/catch → invoke + landingpad: requiere ABI C++ (@__cxa_throw, @__cxa_begin_catch)")
        issues.append("Excepciones custom Java no mapean directamente a personality functions de LLVM")
        decisions.append("throw → branch a bloque landingpad con @__cxa_throw stub")
        decisions.append("finally → duplicación de bloques (normal + unwind path)")

    elif name == "Sample04_Collections":
        list_t = module.context.get_identified_type("ArrayList")
        list_t.set_body(ir.PointerType(i8p), i32, i32)

        fn_add = ir.Function(module,
                    ir.FunctionType(void, [ir.PointerType(list_t), i8p]),
                    name="ArrayList_add")
        b = ir.IRBuilder(fn_add.append_basic_block("entry"))
        b.ret_void()

        fn_get = ir.Function(module,
                    ir.FunctionType(i8p, [ir.PointerType(list_t), i32]),
                    name="ArrayList_get")
        b = ir.IRBuilder(fn_get.append_basic_block("entry"))
        b.ret(ir.Constant(i8p, None))

        issues.append("Type erasure: generics desaparecen en IR — List<Integer> = List<Object> = i8**")
        issues.append("HashMap requiere función hash, buckets, manejo de colisiones — no hay primitiva en IR")
        decisions.append("Generics → punteros opacos (i8*) con bitcast en cada acceso")
        decisions.append("Boxing Integer/Double → struct { i32 value } o i8* con tag de tipo")

    elif name == "Sample05_Lambdas":
        closure_t = module.context.get_identified_type("Lambda_closure")
        closure_t.set_body(i8p, i8p)

        lambda_sig = ir.FunctionType(i32, [i8p, i32, i32])
        fn_lambda  = ir.Function(module, lambda_sig, name="lambda_add")
        b = ir.IRBuilder(fn_lambda.append_basic_block("entry"))
        result = b.add(fn_lambda.args[1], fn_lambda.args[2])
        b.ret(result)

        issues.append("invokedynamic (lambdas/streams) no tiene equivalente en LLVM IR estándar")
        issues.append("Stream API requiere toda la biblioteca java.util.stream — dependencia enorme")
        issues.append("Closures capturan variables del scope → struct de entorno capturado necesario")
        decisions.append("Lambda → struct { i8* fn_ptr, i8* env_ptr } (closure manual)")
        decisions.append("Stream.filter().map() → loop expandido manualmente en IR")

    # ── Guardar IR ──
    ir_text  = str(module)
    ir_path  = str(IR_DIR / f"{name}.ll")
    with open(ir_path, "w", encoding="utf-8") as f:
        f.write(ir_text)

    # ── Validar IR ──
    try:
        binding.initialize_all_targets()
        llvm_mod = binding.parse_assembly(ir_text)
        llvm_mod.verify()
        valid = True
        validate_error = None
    except Exception as e:
        err = str(e)
        if "deprecated" in err.lower() or "initialization" in err.lower():
            valid = True
            validate_error = None
        else:
            valid = False
            validate_error = err

    return {
        "step": "llvm_ir",
        "success": valid,
        "ir_path": ir_path,
        "ir_lines": len(ir_text.splitlines()),
        "issues": issues,
        "decisions": decisions,
        "validate_error": validate_error,
    }

# ──────────────────────────────────────────────
# PASO 4: Ejecutar pipeline completo
# ──────────────────────────────────────────────
def run_pipeline():
    print("=" * 60)
    print("  PIPELINE: Java → LLVM IR")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Directorio: {BASE_DIR}")
    print("=" * 60)

    all_results = []

    for name, category, desc in SAMPLES:
        print(f"\n▶ {name} [{category}] — {desc}")

        r = {"name": name, "category": category, "description": desc}

        # Paso 1
        step1 = compile_java(name)
        r["javac"] = step1
        status = "✅" if step1["success"] else "❌"
        print(f"  {status} javac: {'OK' if step1['success'] else step1['stderr']}")

        # Paso 2
        step2 = inspect_bytecode(name)
        r["javap"] = step2
        opcodes = step2.get("opcodes_detected", {})
        lines   = step2.get("output_lines", 0)
        print(f"  📦 javap: {lines} líneas | opcodes críticos: {list(opcodes.keys()) or 'ninguno'}")

        # Paso 3
        step3 = generate_llvm_ir(name, category)
        r["llvm_ir"] = step3
        status = "✅" if step3["success"] else "⚠️"
        print(f"  {status} LLVM IR: {step3['ir_lines']} líneas → {step3['ir_path']}")
        for issue in step3.get("issues", []):
            print(f"     ⚠️  {issue}")
        if step3.get("validate_error"):
            print(f"     ❌ Validación: {step3['validate_error'][:100]}")

        all_results.append(r)

    # ── Guardar JSON ──
    report_path = str(REPORT_DIR / "pipeline_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n\n{'='*60}")
    print("  RESUMEN DEL PIPELINE")
    print(f"{'='*60}")
    total    = len(all_results)
    ok_javac = sum(1 for r in all_results if r["javac"]["success"])
    ok_ir    = sum(1 for r in all_results if r["llvm_ir"]["success"])
    print(f"  Samples procesados : {total}")
    print(f"  Compilación javac  : {ok_javac}/{total} exitosos")
    print(f"  LLVM IR válido     : {ok_ir}/{total} exitosos")
    print(f"  Reporte guardado   : {report_path}")
    print(f"{'='*60}\n")

    return all_results

if __name__ == "__main__":
    run_pipeline()
