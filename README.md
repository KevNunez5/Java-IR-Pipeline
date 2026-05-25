# Java-IR-Pipeline
# Pipeline Java → LLVM IR

Herramienta de investigación que transforma código Java a LLVM IR y documenta automáticamente la viabilidad de la transformación para análisis de datasets.

---

## ¿Qué hace este pipeline?

Toma archivos `.java`, los compila, inspecciona su bytecode JVM y genera LLVM IR equivalente — documentando en cada paso qué funciona, qué falla y por qué. El objetivo es medir qué tan traducible es un dataset de código Java a representación de bajo nivel.

```
.java  →  javac  →  .class  →  javap  →  análisis de opcodes  →  llvmlite  →  .ll (LLVM IR)
```

---

## Requisitos

- Python 3.8+
- Java JDK 21 (incluye `javac` y `javap`)
- llvmlite: `pip install llvmlite`

Verificar instalación:
```bash
python --version
java -version
javac -version
python -c "import llvmlite; print(llvmlite.__version__)"
```

---

## Estructura del proyecto

```
java_llvm_pipeline/
├── pipeline.py            # Script principal — corre todo el pipeline
├── generate_report.py     # Genera el reporte científico en markdown
├── README.md
├── samples/               # Archivos .java de entrada
│   ├── Sample01_Basic.java
│   ├── Sample02_OOP.java
│   ├── Sample03_Exceptions.java
│   ├── Sample04_Collections.java
│   └── Sample05_Lambdas.java
├── bytecode/              # .class compilados + análisis javap (generado)
├── llvmir/                # Archivos .ll de LLVM IR generados
└── reports/               # Resultados JSON y reporte markdown
```

---

## Cómo correr el pipeline

### 1. Ir a la carpeta del proyecto
```bash
cd ruta/a/java_llvm_pipeline
```

### 2. Correr el pipeline completo
```bash
python pipeline.py
```

Output esperado:
```
PIPELINE: Java → LLVM IR
▶ Sample01_Basic [Básico]
  ✅ javac: OK
  📦 javap: 113 líneas | opcodes críticos: ['invokedynamic', 'invokevirtual']
  ✅ LLVM IR: 33 líneas
...
  Compilación javac  : 5/5 exitosos
  LLVM IR válido     : 5/5 exitosos
```

### 3. Generar el reporte científico
```bash
python generate_report.py
```

Esto produce `reports/hallazgos_java_llvm_ir.md` con todos los hallazgos listos para incorporar al paper.

### 4. Agregar tus propios archivos Java al dataset
Copia cualquier `.java` a la carpeta `samples/`, agrégalo a la lista `SAMPLES` en `pipeline.py`:
```python
SAMPLES = [
    ...
    ("MiArchivo", "Categoría", "descripción breve"),
]
```
Y vuelve a correr `python pipeline.py`.

---

## Qué nos ayuda a encontrar del dataset

### 1. Opcodes JVM problemáticos por archivo
El pipeline detecta automáticamente 6 opcodes críticos en cada muestra:

| Opcode | Qué indica en el dataset | Complejidad IR |
|---|---|---|
| `invokedynamic` | Lambdas, streams o concatenación de strings moderna | 🔴 Alta |
| `invokeinterface` | Uso de colecciones, interfaces genéricas | 🟠 Media-alta |
| `invokevirtual` | Herencia y polimorfismo | 🟡 Media |
| `checkcast` | Casteos de tipos en runtime | 🟡 Media |
| `athrow` | Manejo de excepciones | 🟡 Media |
| `monitorenter` | Concurrencia y bloques `synchronized` | 🔴 Alta |

### 2. Viabilidad de traducción por característica
El pipeline clasifica cada muestra según qué tan traducible es a IR:

| Característica Java | Viabilidad | Lo que genera el pipeline |
|---|---|---|
| Aritmética, loops, condicionales | 🟢 Alta | IR directo y válido |
| Clases, métodos estáticos | 🟢 Alta | Funciones IR con name mangling |
| Herencia, polimorfismo | 🟡 Media | Structs + function pointers (vtable) |
| Excepciones try/catch | 🟡 Media | Bloques landingpad stub |
| Generics, colecciones | 🟠 Baja | Punteros opacos i8* |
| Lambdas, Stream API | 🔴 Muy baja | Closure struct + limitación documentada |
| Concurrencia (threads) | 🔴 Muy baja | No traducible directamente |

### 3. Lo que el reporte JSON permite analizar
`reports/pipeline_results.json` contiene por cada archivo del dataset:
- Si compiló con `javac`
- Qué opcodes problemáticos tiene y cuántas veces aparecen
- Si el IR se generó y validó correctamente
- Lista de limitaciones específicas encontradas
- Decisiones de traducción aplicadas

Esto permite hacer análisis como:
- ¿Qué porcentaje del dataset usa `invokedynamic`?
- ¿Cuántos archivos son "traducibles directamente" vs "requieren intervención"?
- ¿Qué categorías de código dominan el dataset?

---

## Resultados obtenidos (5 muestras iniciales)

| Métrica | Resultado |
|---|---|
| Compilación exitosa | 5/5 (100%) |
| IR generado y válido | 5/5 (100%) |
| Limitaciones documentadas | 9 en total |
| Opcode más frecuente | `invokedynamic` (26 ocurrencias entre 4 samples) |
| Categoría más problemática | Lambdas y Stream API |
| Categoría más viable | Aritmética y control de flujo |

**Hallazgo clave:** `invokedynamic` aparece incluso en código básico (concatenación de strings con `+`), lo que significa que prácticamente ningún programa Java moderno está libre de este opcode. Esto eleva significativamente la barrera de traducción automática para cualquier dataset real.

---

## Limitaciones conocidas del pipeline

- **L1 — invokedynamic:** Sin equivalente directo en LLVM IR. Afecta lambdas, streams y concatenación de strings moderna.
- **L2 — Garbage Collector:** IR opera sobre memoria manual; se requiere integrar un GC externo para traducción completa.
- **L3 — Type Erasure:** Los generics desaparecen en bytecode; el IR resultante usa punteros opacos (`i8*`).
- **L4 — Excepciones:** Requieren ABI C++ (`@__cxa_throw`, personality functions) no disponible en IR puro.
- **L5 — Biblioteca estándar:** `java.util.*`, `java.lang.*` deben reimplementarse o vincularse externamente.

---

*Pipeline desarrollado para investigación sobre viabilidad de transformación Java → LLVM IR en análisis de datasets.*