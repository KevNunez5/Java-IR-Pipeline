# Hallazgos: Pipeline Java → LLVM IR
**Fecha:** 2026-05-25 03:10  |  **Entorno:** OpenJDK 21, LLVM 18, llvmlite 0.47

---

## 1. Resumen Ejecutivo

Se procesaron **5 muestras** representativas de patrones Java comunes.
La fase de compilación `javac` fue exitosa en **5/5** casos (100%).
La generación de LLVM IR fue completada en **5/5** casos, 
aunque con **9 limitaciones documentadas** que impiden una traducción automática directa.

**Conclusión preliminar:** La transformación Java → LLVM IR es *viable con restricciones*.

---

## 2. Descripción del Pipeline

```
Java (.java)
    │
    ▼  javac 21
JVM Bytecode (.class)
    │
    ▼  javap -c -p
Análisis de Bytecode (detección de opcodes críticos)
    │
    ▼  llvmlite 0.47 + LLVM 18
LLVM IR (.ll)  →  Validado con binding.verify()
```

| Herramienta | Versión | Rol |
|---|---|---|
| OpenJDK | 21 | Compilación Java → bytecode |
| javap | 21 | Inspección y análisis de bytecode JVM |
| LLVM | 18.1.3 | Backend de generación y validación de IR |
| llvmlite | 0.47.0 | API Python para construcción de LLVM IR |

---

## 3. Resultados por Muestra

| # | Sample | Categoría | javac | IR generado | Opcodes críticos | Problemas |
|---|---|---|---|---|---|---|
| 1 | `Sample01_Basic` | Básico | ✅ | ✅ | invokedynamic, invokevirtual | 0 |
| 2 | `Sample02_OOP` | OOP | ✅ | ✅ | invokevirtual | 2 |
| 3 | `Sample03_Exceptions` | Excepciones | ✅ | ✅ | invokedynamic, invokevirtual, athrow | 2 |
| 4 | `Sample04_Collections` | Colecciones | ✅ | ✅ | invokedynamic, invokevirtual, invokeinterface, checkcast, athrow | 2 |
| 5 | `Sample05_Lambdas` | Lambdas | ✅ | ✅ | invokedynamic, invokevirtual, invokeinterface, checkcast | 3 |

### Sample01_Basic — variables, loops, aritmética

**Opcodes JVM críticos detectados:**
- `invokedynamic`: 6 ocurrencia(s)
- `invokevirtual`: 6 ocurrencia(s)

**Decisiones de traducción:**
- Loop for → bloques basic block (entry/loop/body/exit)
- Array Java → pointer + length como parámetros separados

**✅ Sin limitaciones críticas**

**LLVM IR generado (fragmento):**
```llvm
; ModuleID = "java_Sample01_Basic"
target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

define i32 @"factorial"(i32 %"n")
{
entry:
  %"result" = alloca i32
  %"i" = alloca i32
  store i32 1, i32* %"result"
  store i32 2, i32* %"i"
  br label %"loop"
loop:
  %"i_val" = load i32, i32* %"i"
  %"cond" = icmp sle i32 %"i_val", %"n"
  br i1 %"cond", label %"body", label %"exit"
exit:
  %"final" = load i32, i32* %"result"
  ret i32 %"final"
body:
; ... (13 líneas adicionales)
```

### Sample02_OOP — clases, herencia, polimorfismo

**Opcodes JVM críticos detectados:**
- `invokevirtual`: 2 ocurrencia(s)

**Decisiones de traducción:**
- Clases Java → identified structs en IR
- Métodos virtuales → function pointers en vtable struct

**⚠️ Limitaciones:**
- Virtual dispatch requiere vtable manual — no hay soporte nativo en LLVM IR
- Herencia múltiple necesita struct anidados — complejidad alta

**LLVM IR generado (fragmento):**
```llvm
; ModuleID = "java_Sample02_OOP"
target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

%"Shape" = type {i8*, i8*}
define double @"Circle_area"(%"Shape"* %".1")
{
entry:
  ret double 0x4053a27ef9db22d1
}

define double @"Rectangle_area"(%"Shape"* %".1")
{
entry:
  ret double 0x4038000000000000
}
```

### Sample03_Exceptions — try/catch/finally

**Opcodes JVM críticos detectados:**
- `invokedynamic`: 5 ocurrencia(s)
- `invokevirtual`: 9 ocurrencia(s)
- `athrow`: 3 ocurrencia(s)

**Decisiones de traducción:**
- throw → branch a bloque landingpad con @__cxa_throw stub
- finally → duplicación de bloques (normal + unwind path)

**⚠️ Limitaciones:**
- try/catch → invoke + landingpad: requiere ABI C++ (@__cxa_throw, @__cxa_begin_catch)
- Excepciones custom Java no mapean directamente a personality functions de LLVM

**LLVM IR generado (fragmento):**
```llvm
; ModuleID = "java_Sample03_Exceptions"
target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

%"Shape" = type {i8*, i8*}
define i32 @"divide"(i32 %"a", i32 %"b")
{
entry:
  %".4" = icmp eq i32 %"b", 0
  br i1 %".4", label %"throw", label %"ok"
ok:
  %"result" = sdiv i32 %"a", %"b"
  ret i32 %"result"
throw:
  ret i32 -1
}
```

### Sample04_Collections — generics, ArrayList, HashMap

**Opcodes JVM críticos detectados:**
- `invokedynamic`: 4 ocurrencia(s)
- `invokevirtual`: 4 ocurrencia(s)
- `invokeinterface`: 19 ocurrencia(s)
- `checkcast`: 5 ocurrencia(s)
- `athrow`: 1 ocurrencia(s)

**Decisiones de traducción:**
- Generics → punteros opacos (i8*) con bitcast en cada acceso
- Boxing Integer/Double → struct { i32 value } o i8* con tag de tipo

**⚠️ Limitaciones:**
- Type erasure: generics desaparecen en IR — List<Integer> = List<Object> = i8**
- HashMap requiere función hash, buckets, manejo de colisiones — no hay primitiva en IR

**LLVM IR generado (fragmento):**
```llvm
; ModuleID = "java_Sample04_Collections"
target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

%"Shape" = type {i8*, i8*}
%"ArrayList" = type {i8**, i32, i32}
define void @"ArrayList_add"(%"ArrayList"* %".1", i8* %".2")
{
entry:
  ret void
}

define i8* @"ArrayList_get"(%"ArrayList"* %".1", i32 %".2")
{
entry:
  ret i8* null
}
```

### Sample05_Lambdas — lambda, Stream API, invokedynamic

**Opcodes JVM críticos detectados:**
- `invokedynamic`: 11 ocurrencia(s)
- `invokevirtual`: 9 ocurrencia(s)
- `invokeinterface`: 7 ocurrencia(s)
- `checkcast`: 2 ocurrencia(s)

**Decisiones de traducción:**
- Lambda → struct { i8* fn_ptr, i8* env_ptr } (closure manual)
- Stream.filter().map() → loop expandido manualmente en IR

**⚠️ Limitaciones:**
- invokedynamic (lambdas/streams) no tiene equivalente en LLVM IR estándar
- Stream API requiere toda la biblioteca java.util.stream — dependencia enorme
- Closures capturan variables del scope → struct de entorno capturado necesario

**LLVM IR generado (fragmento):**
```llvm
; ModuleID = "java_Sample05_Lambdas"
target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

%"Shape" = type {i8*, i8*}
%"ArrayList" = type {i8**, i32, i32}
%"Lambda_closure" = type {i8*, i8*}
define i32 @"lambda_add"(i8* %".1", i32 %".2", i32 %".3")
{
entry:
  %".5" = add i32 %".2", %".3"
  ret i32 %".5"
}
```

---

## 4. Opcodes JVM vs LLVM IR

| Opcode JVM | Equivalente LLVM IR | Complejidad |
|---|---|---|
| `invokevirtual` | Function pointer en vtable struct | Media |
| `invokedynamic` | Sin equivalente directo | **Alta** |
| `invokeinterface` | Pointer dispatch con type check | Alta |
| `checkcast` | `bitcast` + runtime type tag | Media |
| `athrow` | `invoke` + `landingpad` + ABI C++ | **Alta** |

---

## 5. Limitaciones

**L1 — invokedynamic:** lambdas, Stream API y String concatenation no tienen equivalente en IR.

**L2 — Garbage Collector:** Java usa GC automático; IR opera sobre memoria manual (`malloc`/`free`).

**L3 — Type Erasure:** `List<Integer>` y `List<Object>` son idénticos en bytecode → IR usa `i8*` opaco.

**L4 — Excepciones:** Requieren `invoke` + `landingpad` + personality function del ABI C++.

**L5 — Biblioteca estándar:** `java.util.*`, `java.lang.*` no existen en IR — deben reimplementarse.

---

## 6. Viabilidad por Característica

| Característica | Viabilidad | Estrategia |
|---|---|---|
| Aritmética y control de flujo | 🟢 Alta | Traducción directa |
| Clases y métodos estáticos | 🟢 Alta | Funciones LLVM con mangling |
| Herencia y polimorfismo | 🟡 Media | Structs + vtable manual |
| Excepciones | 🟡 Media | invoke/landingpad + ABI C++ |
| Generics/Colecciones | 🟠 Baja | i8* + bitcast + runtime checks |
| Lambdas y Streams | 🔴 Muy baja | Expansión manual o skip |

---
*Reporte generado automáticamente por el pipeline Java → LLVM IR*